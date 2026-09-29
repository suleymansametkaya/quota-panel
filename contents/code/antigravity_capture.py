#!/usr/bin/env python3
"""Capture only model quota fields from the official Antigravity CLI status line."""

import datetime
import math
import sys
import time
from pathlib import Path
from quota_io import atomic_write_json, read_limited_json_stream


def reset_timestamp(value):
    if isinstance(value, (int, float)):
        try:
            timestamp = float(value)
            return int(timestamp) if math.isfinite(timestamp) else None
        except (OverflowError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return int(datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except (ValueError, OverflowError):
            return None
    return None


def main():
    payload = read_limited_json_stream(sys.stdin)
    quotas = (payload.get("quota") or {}) if isinstance(payload, dict) else {}
    if not isinstance(quotas, dict):
        return
    windows = []
    for name, details in list(quotas.items())[:12]:
        if not isinstance(details, dict):
            continue
        try:
            remaining = float(details["remaining_fraction"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(remaining):
            continue
        remaining = max(0.0, min(1.0, remaining))
        window = {"name": str(name)[:80], "used": round((1 - remaining) * 100)}
        reset = reset_timestamp(details.get("reset_time"))
        if reset is None and details.get("reset_in_seconds") is not None:
            try:
                seconds = float(details["reset_in_seconds"])
                reset = int(time.time() + seconds) if math.isfinite(seconds) else None
            except (TypeError, ValueError, OverflowError):
                pass
        if reset is not None:
            window["resetsAt"] = reset
        windows.append(window)
    if not windows:
        print("Antigravity · kota verisi bekleniyor")
        return

    target = Path.home() / ".config" / "quota-panel" / "antigravity.json"
    atomic_write_json(target, {"updatedAt": int(time.time()), "windows": windows})
    print("Antigravity · " + " · ".join(
        f"{item['name']} %{100 - item['used']}" for item in windows[:2]))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, OverflowError):
        print("Antigravity · kota verisi bekleniyor")
