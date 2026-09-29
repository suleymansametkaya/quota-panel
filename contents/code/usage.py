#!/usr/bin/env python3
"""Read quota snapshots without exposing account credentials to the QML widget."""

import json
import argparse
import datetime
import math
import os
import re
import selectors
import shutil
import subprocess
import sys
import time
from pathlib import Path
from quota_io import MAX_JSON_BYTES, atomic_write_json, parse_limited_json, read_limited_json

CACHE = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "quota-panel"
ANTIGRAVITY_MIN_REFRESH_SECONDS = 60
MAX_CODEX_PROTOCOL_LINE_BYTES = 1024 * 1024


def read_json(path):
    try:
        return read_limited_json(path)
    except (OSError, ValueError):
        return None


def run_bounded_stdout(command, *, timeout, output_limit):
    """Run a child while bounding captured stdout as well as execution time."""
    proc = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, bufsize=0,
    )
    selector = selectors.DefaultSelector()
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        selector.register(proc.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            if not selector.select(remaining):
                raise subprocess.TimeoutExpired(command, timeout)
            chunk = os.read(proc.stdout.fileno(), min(65536, output_limit + 1 - len(output)))
            if not chunk:
                return proc.wait(timeout=max(0, deadline - time.monotonic())), bytes(output)
            output.extend(chunk)
            if len(output) > output_limit:
                raise ValueError("Provider output exceeds the size limit")
    finally:
        selector.close()
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def save_json(path, data):
    try:
        atomic_write_json(path, data)
    except OSError:
        pass


def used_percent(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return round(max(0.0, min(100.0, number)))


def safe_epoch_seconds(value):
    """Return a finite nonnegative epoch timestamp, or None when invalid."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(timestamp) or timestamp < 0 or timestamp > 8.64e15:
        return None
    return int(timestamp) if timestamp.is_integer() else timestamp


def cache_age_seconds(value, now):
    """Return a safe cache age, or None when the stored timestamp is invalid."""
    timestamp = safe_epoch_seconds(value)
    if timestamp is None or timestamp > now + 300:
        return None
    return max(0, now - timestamp)


def safe_reset_time(value):
    """Keep only finite epoch timestamps or parseable, bounded ISO timestamps."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return value if math.isfinite(number) and 0 < number <= 8.64e15 else None
    if not isinstance(value, str) or len(value) > 128:
        return None
    try:
        number = float(value)
        if math.isfinite(number) and 0 < number <= 8.64e15:
            return int(number) if number.is_integer() else number
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        timestamp = parsed.timestamp()
    except (ValueError, OverflowError, OSError):
        return None
    return value if math.isfinite(timestamp) and 0 < timestamp <= 253402300799 else None


def window_duration_label(value):
    if isinstance(value, bool) or value is None:
        return "Süre bilinmiyor"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "Süre bilinmiyor"
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        return "Süre bilinmiyor"
    mins = int(number)
    if mins == 10080:
        return "Haftalık"
    if mins and mins < 1440 and mins % 60 == 0:
        return f"{mins // 60} saat"
    if mins and mins % 1440 == 0:
        return f"{mins // 1440} gün"
    return f"{mins} dk"


def reset_credit_count(snapshot):
    if not isinstance(snapshot, dict):
        return None
    credits = snapshot.get("rateLimitResetCredits")
    if not isinstance(credits, dict):
        return None
    value = credits.get("availableCount")
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        return None
    return int(number)


def codex_limits():
    binary = shutil.which("codex") or "/usr/bin/codex"
    if not Path(binary).exists():
        raise RuntimeError("Codex CLI bulunamadı")
    proc = subprocess.Popen(
        [binary, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, bufsize=0,
    )
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 12
    try:
        init = {"method": "initialize", "id": 1, "params": {
            "clientInfo": {"name": "quota_panel", "title": "Quota Panel", "version": "1.0.0"}}}
        proc.stdin.write((json.dumps(init) + "\n").encode("utf-8"))
        proc.stdin.flush()
        initialized = False
        pending = bytearray()
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                break
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                break
            pending.extend(chunk)
            if len(pending) > MAX_CODEX_PROTOCOL_LINE_BYTES and b"\n" not in pending:
                raise RuntimeError("Codex yanıt satırı çok uzun")
            while b"\n" in pending:
                line, _, rest = pending.partition(b"\n")
                pending = bytearray(rest)
                if len(line) > MAX_CODEX_PROTOCOL_LINE_BYTES:
                    raise RuntimeError("Codex yanıt satırı çok uzun")
                try:
                    message = json.loads(line.decode("utf-8"))
                except (UnicodeError, ValueError):
                    continue
                if not isinstance(message, dict):
                    continue
                if message.get("id") == 1:
                    if "error" in message:
                        raise RuntimeError("Codex bağlantısı açılamadı")
                    initialized = True
                    proc.stdin.write((json.dumps({"method": "initialized", "params": {}}) + "\n").encode("utf-8"))
                    proc.stdin.write((json.dumps({"method": "account/rateLimits/read", "id": 2, "params": {}}) + "\n").encode("utf-8"))
                    proc.stdin.flush()
                elif message.get("id") == 2 and initialized:
                    if "error" in message:
                        raise RuntimeError("Codex limitleri okunamadı")
                    return message.get("result") or {}
        raise RuntimeError("Codex yanıt vermedi")
    finally:
        selector.close()
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def windows_from_codex(snapshot):
    if not isinstance(snapshot, dict):
        return []
    buckets = snapshot.get("rateLimitsByLimitId") or {}
    if not isinstance(buckets, dict):
        buckets = {}
    if not buckets and snapshot.get("rateLimits"):
        buckets = {"codex": snapshot["rateLimits"]}
    windows = []
    for key, bucket in buckets.items():
        if not isinstance(bucket, dict):
            continue
        bucket_name = bucket.get("limitName") or ("Codex" if key == "codex" else key)
        for part in ("primary", "secondary"):
            value = bucket.get(part)
            if not isinstance(value, dict) or value.get("usedPercent") is None:
                continue
            used = used_percent(value["usedPercent"])
            if used is None:
                continue
            duration = window_duration_label(value.get("windowDurationMins"))
            window = {"name": f"{bucket_name} · {duration}", "used": used}
            reset = safe_reset_time(value.get("resetsAt"))
            if reset is not None:
                window["resetsAt"] = reset
            windows.append(window)
    return windows


def windows_from_claude(snapshot):
    if not isinstance(snapshot, dict):
        return []
    labels = (("five_hour", "5 Saatlik"), ("seven_day", "Haftalık"))
    windows = []
    for key, label in labels:
        value = snapshot.get(key)
        if isinstance(value, dict) and value.get("used_percentage") is not None:
            used = used_percent(value["used_percentage"])
            if used is None:
                continue
            window = {"name": label, "used": used}
            reset = safe_reset_time(value.get("resets_at"))
            if reset is not None:
                window["resetsAt"] = reset
            windows.append(window)
    return windows


def external_windows(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("windows"), list):
        return []
    windows = []
    labels = {"3p-5h": "Claude ve OpenAI Modelleri · 5 Saat",
              "3p-weekly": "Claude ve OpenAI Modelleri · Haftalık",
              "gemini-5h": "Gemini · 5 Saat",
              "gemini-weekly": "Gemini · Haftalık"}
    for item in snapshot["windows"][:12]:
        if not isinstance(item, dict):
            continue
        try:
            used = float(item["used"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(used):
            continue
        used = max(0, min(100, used))
        raw_name = str(item.get("name") or "Kullanım")[:80]
        window = {"name": labels.get(raw_name, raw_name), "used": round(used)}
        if item.get("resetsAt") is not None:
            reset = safe_reset_time(item["resetsAt"])
            if reset is not None:
                window["resetsAt"] = reset
        windows.append(window)
    order = {"Gemini · 5 Saat": 0,
             "Gemini · Haftalık": 1,
             "Claude ve OpenAI Modelleri · 5 Saat": 2,
             "Claude ve OpenAI Modelleri · Haftalık": 3}
    windows.sort(key=lambda window: order.get(window["name"], 4))
    return windows


def antigravity_limits():
    """Read the official CLI's non-interactive, read-only /usage response."""
    binary = shutil.which("agy") or str(Path.home() / ".local" / "bin" / "agy")
    if not Path(binary).exists():
        return []
    try:
        returncode, output = run_bounded_stdout(
            [binary, "-p", "/usage", "--output-format", "json", "--print-timeout", "20s"],
            timeout=25, output_limit=MAX_JSON_BYTES,
        )
        if returncode != 0:
            return []
        result = parse_limited_json(output)
    except (OSError, UnicodeError, ValueError, RecursionError, subprocess.TimeoutExpired):
        return []
    if not isinstance(result, dict) or result.get("status") != "SUCCESS" or not isinstance(result.get("response"), str):
        return []

    names = {
        ("Gemini Models", "Five Hour Limit Remaining"): "gemini-5h",
        ("Gemini Models", "Weekly Limit Remaining"): "gemini-weekly",
        ("Claude and GPT models", "Five Hour Limit Remaining"): "3p-5h",
        ("Claude and GPT models", "Weekly Limit Remaining"): "3p-weekly",
    }
    windows = []
    for line in result["response"].splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            continue
        name = names.get((fields[0].strip(), fields[1].strip()))
        percent = re.fullmatch(r"(100(?:\.0+)?|\d{1,2}(?:\.\d+)?)%", fields[2].strip())
        if not name or not percent:
            continue
        try:
            reset = int(datetime.datetime.fromisoformat(fields[3].strip().replace("Z", "+00:00")).timestamp())
        except ValueError:
            continue
        windows.append({"name": name, "used": round(100 - float(percent.group(1))),
                        "resetsAt": reset})
    return windows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--antigravity-source", default="")
    parser.add_argument("--providers", default="codex,claude,antigravity",
                        help="Comma-separated provider IDs to read")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()
    enabled = {item.strip() for item in args.providers.split(",")}
    now = int(time.time())
    providers = []
    if "codex" in enabled:
        codex = {"id": "codex", "name": "Codex", "state": "unavailable", "windows": [],
                 "message": "Veri alınamadı"}
        cache_file = CACHE / "codex.json"
        cached = read_json(cache_file)
        try:
            snapshot = codex_limits()
            windows = windows_from_codex(snapshot)
            if windows:
                codex.update(state="ok", windows=windows, message="", updatedAt=now,
                             resetCredits=reset_credit_count(snapshot))
                save_json(cache_file, codex)
        except (OSError, RuntimeError, ValueError):
            age = cache_age_seconds(cached.get("updatedAt"), now) if isinstance(cached, dict) else None
            if age is not None and age < 1800:
                codex = cached
                codex["state"] = "stale"
                codex["message"] = "Son alınan veri"
        providers.append(codex)

    if "claude" in enabled:
        claude = {"id": "claude", "name": "Claude", "state": "unavailable", "windows": [],
                  "message": "Claude Code oturumunda ilk yanıttan sonra limit verisi görünür"}
        claude_data = read_json(CACHE / "claude.json")
        if isinstance(claude_data, dict):
            windows = windows_from_claude(claude_data.get("rate_limits") or {})
            updated = claude_data.get("updatedAt", 0)
            age = cache_age_seconds(updated, now)
            if windows and age is not None and age < 86400:
                claude.update(state="ok" if age < 900 else "stale", windows=windows,
                              message="" if age < 900 else "Son Claude oturumundan",
                              updatedAt=updated)
        providers.append(claude)

    if "antigravity" in enabled:
        antigravity = {"id": "antigravity", "name": "Antigravity", "state": "unavailable",
                       "windows": [], "message": "CLI oturumundan henüz kota verisi gelmedi"}
        external_path = (Path(args.antigravity_source).expanduser() if args.antigravity_source
                         else Path.home() / ".config" / "quota-panel" / "antigravity.json")
        external = read_json(external_path)
        if not args.antigravity_source:
            cached_at = safe_epoch_seconds(external.get("updatedAt")) if isinstance(external, dict) else None
            if cached_at is None:
                try:
                    cached_at = safe_epoch_seconds(external_path.stat().st_mtime)
                except OSError:
                    cached_at = None
            attempt_cache = CACHE / "antigravity-refresh.json"
            last_attempt = read_json(attempt_cache)
            last_attempt_at = safe_epoch_seconds(last_attempt.get("attemptedAt")) if isinstance(last_attempt, dict) else None
            last_attempt_age = cache_age_seconds(last_attempt_at, now)
            cooldown_elapsed = last_attempt_age is None or last_attempt_age >= ANTIGRAVITY_MIN_REFRESH_SECONDS
            cache_age = cache_age_seconds(cached_at, now)
            cache_expired = cache_age is None or cache_age >= ANTIGRAVITY_MIN_REFRESH_SECONDS
            # Manual refresh bypasses cache age, but still respects the one-minute CLI cooldown.
            if cooldown_elapsed and (args.force_refresh or cache_expired):
                save_json(attempt_cache, {"attemptedAt": now})
                fresh_windows = antigravity_limits()
                if fresh_windows:
                    external = {"updatedAt": int(time.time()), "windows": fresh_windows}
                    save_json(external_path, external)
        windows = external_windows(external)
        if windows:
            updated = safe_epoch_seconds(external.get("updatedAt")) if isinstance(external, dict) else None
            if updated is None:
                try:
                    updated = safe_epoch_seconds(external_path.stat().st_mtime)
                except OSError:
                    updated = None
            age = cache_age_seconds(updated, now)
            if age is not None:
                antigravity.update(state="ok" if age < 900 else "stale", windows=windows,
                                   message="" if age < 900 else "Son Antigravity oturumundan",
                                   updatedAt=updated)
        providers.append(antigravity)

    print(json.dumps({"updatedAt": now, "providers": providers},
                     ensure_ascii=False, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
