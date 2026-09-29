#!/usr/bin/env python3
"""Claude Code statusLine receiver: cache quota fields only, never credentials."""

import json
import math
import os
import sys
import time
from pathlib import Path
from quota_io import atomic_write_json


try:
    incoming = json.load(sys.stdin)
    rate_limits = (incoming.get("rate_limits") or {}) if isinstance(incoming, dict) else {}
    safe = {}
    if isinstance(rate_limits, dict):
        for key in ("five_hour", "seven_day"):
            value = rate_limits.get(key)
            if not isinstance(value, dict) or value.get("used_percentage") is None:
                continue
            try:
                used = float(value["used_percentage"])
            except (TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(used):
                continue
            safe[key] = {"used_percentage": max(0.0, min(100.0, used)),
                         "resets_at": value.get("resets_at")}
    if safe:
        directory = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "quota-panel"
        target = directory / "claude.json"
        atomic_write_json(target, {"updatedAt": int(time.time()), "rate_limits": safe})
        parts = []
        for key, label in (("five_hour", "5s"), ("seven_day", "7g")):
            if key in safe and safe[key].get("used_percentage") is not None:
                parts.append(f"{label} %{round(float(safe[key]['used_percentage']))}")
        print("Claude " + " · ".join(parts))
    else:
        print("Claude · limit verisi bekleniyor")
except (OSError, ValueError, TypeError):
    pass
