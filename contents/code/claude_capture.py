#!/usr/bin/env python3
"""Claude Code statusLine receiver: cache quota fields only, never credentials."""

import json
import os
import sys
import time
from pathlib import Path

try:
    incoming = json.load(sys.stdin)
    rate_limits = incoming.get("rate_limits") or {}
    safe = {key: {field: value.get(field) for field in ("used_percentage", "resets_at")}
            for key in ("five_hour", "seven_day")
            if isinstance(value := rate_limits.get(key), dict)}
    if safe:
        directory = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "quota-panel"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "claude.json"
        temp = directory / "claude.tmp"
        temp.write_text(json.dumps({"updatedAt": int(time.time()), "rate_limits": safe}), encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(target)
        parts = []
        for key, label in (("five_hour", "5s"), ("seven_day", "7g")):
            if key in safe and safe[key].get("used_percentage") is not None:
                parts.append(f"{label} %{round(float(safe[key]['used_percentage']))}")
        print("Claude " + " · ".join(parts))
    else:
        print("Claude · limit verisi bekleniyor")
except (OSError, ValueError, TypeError):
    pass
