#!/usr/bin/env python3
"""Read quota snapshots without exposing account credentials to the QML widget."""

import json
import argparse
import datetime
import os
import re
import selectors
import shutil
import subprocess
import sys
import time
from pathlib import Path

CACHE = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "quota-panel"


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(path)
    except OSError:
        pass


def codex_limits():
    binary = shutil.which("codex") or "/usr/bin/codex"
    if not Path(binary).exists():
        raise RuntimeError("Codex CLI bulunamadı")
    proc = subprocess.Popen(
        [binary, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, bufsize=1,
    )
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 12
    try:
        init = {"method": "initialize", "id": 1, "params": {
            "clientInfo": {"name": "quota_panel", "title": "Quota Panel", "version": "1.0.0"}}}
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        initialized = False
        while time.monotonic() < deadline:
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            line = proc.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError("Codex bağlantısı açılamadı")
                initialized = True
                proc.stdin.write(json.dumps({"method": "initialized", "params": {}}) + "\n")
                proc.stdin.write(json.dumps({"method": "account/rateLimits/read", "id": 2, "params": {}}) + "\n")
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
    buckets = snapshot.get("rateLimitsByLimitId") or {}
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
            mins = value.get("windowDurationMins") or 0
            duration = f"{mins // 60} saat" if mins and mins < 1440 and mins % 60 == 0 else (
                f"{mins // 1440} gün" if mins and mins % 1440 == 0 else f"{mins} dk")
            windows.append({"name": f"{bucket_name} · {duration}",
                            "used": round(float(value["usedPercent"])),
                            "resetsAt": value.get("resetsAt")})
    return windows


def windows_from_claude(snapshot):
    labels = (("five_hour", "5 saatlik"), ("seven_day", "Haftalık"))
    windows = []
    for key, label in labels:
        value = snapshot.get(key)
        if isinstance(value, dict) and value.get("used_percentage") is not None:
            windows.append({"name": label, "used": round(float(value["used_percentage"])),
                            "resetsAt": value.get("resets_at")})
    return windows


def external_windows(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("windows"), list):
        return []
    windows = []
    labels = {"3p-5h": "Diğer modeller · 5 saat",
              "3p-weekly": "Diğer modeller · haftalık",
              "gemini-5h": "Gemini · 5 saat",
              "gemini-weekly": "Gemini · haftalık"}
    for item in snapshot["windows"][:12]:
        if not isinstance(item, dict):
            continue
        try:
            used = max(0, min(100, float(item["used"])))
        except (KeyError, TypeError, ValueError):
            continue
        raw_name = str(item.get("name") or "Kullanım")[:80]
        window = {"name": labels.get(raw_name, raw_name), "used": round(used)}
        if item.get("resetsAt") is not None:
            try:
                window["resetsAt"] = int(item["resetsAt"])
            except (TypeError, ValueError):
                pass
        windows.append(window)
    order = {"Gemini · 5 saat": 0,
             "Gemini · haftalık": 1,
             "Diğer modeller · 5 saat": 2,
             "Diğer modeller · haftalık": 3}
    windows.sort(key=lambda window: order.get(window["name"], 4))
    return windows


def antigravity_limits():
    """Read the official CLI's non-interactive, read-only /usage response."""
    binary = shutil.which("agy") or str(Path.home() / ".local" / "bin" / "agy")
    if not Path(binary).exists():
        return []
    try:
        proc = subprocess.run(
            [binary, "-p", "/usage", "--output-format", "json", "--print-timeout", "20s"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=25, check=False,
        )
        if proc.returncode != 0:
            return []
        result = json.loads(proc.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
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
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()
    now = int(time.time())
    codex = {"id": "codex", "name": "Codex", "state": "unavailable", "windows": [],
             "message": "Veri alınamadı"}
    cache_file = CACHE / "codex.json"
    cached = read_json(cache_file)
    try:
        snapshot = codex_limits()
        windows = windows_from_codex(snapshot)
        if windows:
            codex.update(state="ok", windows=windows, message="", updatedAt=now,
                         resetCredits=(snapshot.get("rateLimitResetCredits") or {}).get("availableCount"))
            save_json(cache_file, codex)
    except (OSError, RuntimeError, ValueError):
        if isinstance(cached, dict) and now - cached.get("updatedAt", 0) < 1800:
            codex = cached
            codex["state"] = "stale"
            codex["message"] = "Son alınan veri"

    claude = {"id": "claude", "name": "Claude", "state": "unavailable", "windows": [],
              "message": "Claude Code oturumunda ilk yanıttan sonra limit verisi görünür"}
    claude_data = read_json(CACHE / "claude.json")
    if isinstance(claude_data, dict):
        windows = windows_from_claude(claude_data.get("rate_limits") or {})
        updated = claude_data.get("updatedAt", 0)
        if windows and now - updated < 86400:
            claude.update(state="ok" if now - updated < 900 else "stale", windows=windows,
                          message="" if now - updated < 900 else "Son Claude oturumundan",
                          updatedAt=updated)

    antigravity = {"id": "antigravity", "name": "Antigravity", "state": "unavailable",
                   "windows": [], "message": "CLI oturumundan henüz kota verisi gelmedi"}
    external_path = (Path(args.antigravity_source).expanduser() if args.antigravity_source
                     else Path.home() / ".config" / "quota-panel" / "antigravity.json")
    external = read_json(external_path)
    if not args.antigravity_source:
        try:
            cached_at = int(external.get("updatedAt") or external_path.stat().st_mtime) if isinstance(external, dict) else 0
        except (OSError, TypeError, ValueError):
            cached_at = 0
        if args.force_refresh or now - cached_at >= 60:
            fresh_windows = antigravity_limits()
            if fresh_windows:
                external = {"updatedAt": int(time.time()), "windows": fresh_windows}
                save_json(external_path, external)
    windows = external_windows(external)
    if windows:
        try:
            updated = int(external.get("updatedAt") or external_path.stat().st_mtime)
        except (OSError, TypeError, ValueError):
            updated = 0
        fresh = now - updated < 900
        antigravity.update(state="ok" if fresh else "stale", windows=windows,
                           message="" if fresh else "Son Antigravity oturumundan",
                           updatedAt=updated)

    print(json.dumps({"updatedAt": now, "providers": [codex, claude, antigravity]},
                     ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
