#!/usr/bin/env python3
"""Capture only model quota fields from the official Antigravity CLI status line."""

import datetime
import json
import os
import sys
import time
from pathlib import Path


def reset_timestamp(value):
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return None
    return None


def main():
    payload = json.load(sys.stdin)
    quotas = payload.get("quota") or {}
    if not isinstance(quotas, dict):
        return
    windows = []
    for name, details in list(quotas.items())[:12]:
        if not isinstance(details, dict):
            continue
        try:
            remaining = max(0.0, min(1.0, float(details["remaining_fraction"])))
        except (KeyError, TypeError, ValueError):
            continue
        window = {"name": str(name)[:80], "used": round((1 - remaining) * 100)}
        reset = reset_timestamp(details.get("reset_time"))
        if reset is None and details.get("reset_in_seconds") is not None:
            try:
                reset = int(time.time() + float(details["reset_in_seconds"]))
            except (TypeError, ValueError):
                pass
        if reset is not None:
            window["resetsAt"] = reset
        windows.append(window)
    if not windows:
        print("Antigravity · kota verisi bekleniyor")
        return

    target = Path.home() / ".config" / "quota-panel" / "antigravity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps({"updatedAt": int(time.time()), "windows": windows},
                               ensure_ascii=False), encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(target)
    print("Antigravity · " + " · ".join(
        f"{item['name']} %{100 - item['used']}" for item in windows[:2]))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError):
        print("Antigravity · kota verisi bekleniyor")
