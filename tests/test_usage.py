import math
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CODE_DIR = Path(__file__).resolve().parents[1] / "contents" / "code"
sys.path.insert(0, str(CODE_DIR))

import usage  # noqa: E402


class UsageParsingTests(unittest.TestCase):
    def test_used_percent_rejects_non_finite_and_clamps_range(self):
        self.assertIsNone(usage.used_percent(math.nan))
        self.assertIsNone(usage.used_percent(math.inf))
        self.assertIsNone(usage.used_percent("not a number"))
        self.assertEqual(usage.used_percent(-4), 0)
        self.assertEqual(usage.used_percent(101), 100)

    def test_codex_parser_handles_invalid_duration_and_credit_schema(self):
        snapshot = {
            "rateLimitsByLimitId": {
                "codex": {
                    "primary": {"usedPercent": 25, "windowDurationMins": "bad"},
                    "secondary": {"usedPercent": math.nan, "windowDurationMins": 10080},
                }
            },
            "rateLimitResetCredits": [3],
        }
        windows = usage.windows_from_codex(snapshot)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["used"], 25)
        self.assertTrue(windows[0]["name"].endswith("Süre bilinmiyor"))
        self.assertIsNone(usage.reset_credit_count(snapshot))
        self.assertEqual(usage.reset_credit_count({"rateLimitResetCredits": {"availableCount": 2}}), 2)

    def test_seven_day_window_uses_weekly_label(self):
        windows = usage.windows_from_codex({"rateLimits": {
            "primary": {"usedPercent": 12, "windowDurationMins": 10080},
        }})
        self.assertEqual(windows[0]["name"], "Codex · Haftalık")

    def test_claude_parser_ignores_invalid_cache_values(self):
        self.assertEqual(usage.windows_from_claude("broken"), [])
        self.assertEqual(
            usage.windows_from_claude({"five_hour": {"used_percentage": math.inf}}),
            [],
        )

    def test_external_parser_skips_non_finite_usage(self):
        windows = usage.external_windows({"windows": [
            {"name": "NaN", "used": math.nan},
            {"name": "Valid", "used": 42},
        ]})
        self.assertEqual(windows, [{"name": "Valid", "used": 42}])

    def test_cache_age_rejects_malformed_and_non_finite_timestamps(self):
        for value in ("broken", math.nan, math.inf, -1, True, None):
            with self.subTest(value=value):
                self.assertIsNone(usage.cache_age_seconds(value, 1000))
        self.assertEqual(usage.cache_age_seconds(900, 1000), 100)
        self.assertIsNone(usage.safe_epoch_seconds(math.inf))
        self.assertEqual(usage.safe_epoch_seconds("900"), 900)

    def test_codex_refresh_failure_ignores_malformed_cache_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / "codex.json").write_text(
                json.dumps({"updatedAt": "broken", "windows": [{"used": 1}]}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with mock.patch.object(usage, "CACHE", cache), \
                    mock.patch.object(usage, "codex_limits", side_effect=RuntimeError("offline")), \
                    mock.patch.object(sys, "argv", ["usage.py", "--providers", "codex"]), \
                    contextlib.redirect_stdout(output):
                usage.main()
            provider = json.loads(output.getvalue())["providers"][0]
            self.assertEqual(provider["state"], "unavailable")

    def test_claude_cache_with_malformed_timestamp_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / "claude.json").write_text(json.dumps({
                "updatedAt": "broken",
                "rate_limits": {"five_hour": {"used_percentage": 20}},
            }), encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(usage, "CACHE", cache), \
                    mock.patch.object(sys, "argv", ["usage.py", "--providers", "claude"]), \
                    contextlib.redirect_stdout(output):
                usage.main()
            provider = json.loads(output.getvalue())["providers"][0]
            self.assertEqual(provider["state"], "unavailable")

    def test_external_infinite_reset_time_is_ignored_without_crashing(self):
        windows = usage.external_windows({"windows": [{
            "name": "Valid", "used": 42, "resetsAt": math.inf,
        }]})
        self.assertEqual(windows, [{"name": "Valid", "used": 42}])

    def test_antigravity_non_finite_cache_times_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            cache = home / "cache"
            cache.mkdir()
            external = home / ".config" / "quota-panel" / "antigravity.json"
            external.parent.mkdir(parents=True)
            external.write_text(
                '{"updatedAt": Infinity, "windows": [{"name": "Valid", "used": 42}]}',
                encoding="utf-8",
            )
            (cache / "antigravity-refresh.json").write_text(
                '{"attemptedAt": Infinity}', encoding="utf-8",
            )
            output = io.StringIO()
            with mock.patch.object(usage, "CACHE", cache), \
                    mock.patch("pathlib.Path.home", return_value=home), \
                    mock.patch.object(sys, "argv", ["usage.py", "--providers", "antigravity"]), \
                    contextlib.redirect_stdout(output):
                usage.main()
            provider = json.loads(output.getvalue())["providers"][0]
            self.assertEqual(provider["windows"], [{"name": "Valid", "used": 42}])

    def test_provider_reset_values_are_json_safe(self):
        snapshot = {"rateLimits": {"primary": {
            "usedPercent": 25, "windowDurationMins": 300, "resetsAt": math.nan,
        }}}
        windows = usage.windows_from_codex(snapshot)
        self.assertEqual(windows, [{"name": "Codex · 5 saat", "used": 25}])
        self.assertEqual(json.loads(json.dumps(windows, allow_nan=False)), windows)


if __name__ == "__main__":
    unittest.main()
