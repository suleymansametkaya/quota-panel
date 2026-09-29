import json
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

CODE_DIR = Path(__file__).resolve().parents[1] / "contents" / "code"
sys.path.insert(0, str(CODE_DIR))

from quota_io import (MAX_JSON_BYTES, atomic_write_json, backup_file,
                      read_limited_json_stream)  # noqa: E402


class QuotaIOTests(unittest.TestCase):
    def test_concurrent_atomic_writes_leave_valid_private_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "snapshot.json"
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda number: atomic_write_json(target, {"number": number}), range(40)))

            self.assertIsInstance(json.loads(target.read_text(encoding="utf-8")), dict)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(list(root.glob(".snapshot.json.*.tmp")), [])

    def test_backup_is_unique_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "settings.json"
            source.write_text('{"keep": true}', encoding="utf-8")

            first = backup_file(source, prefix="settings-backup-")
            second = backup_file(source, prefix="settings-backup-")

            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding="utf-8"), '{"keep": true}')
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)

    def test_provider_json_stream_is_bounded_and_accepts_valid_input(self):
        import io

        self.assertEqual(read_limited_json_stream(io.BytesIO(b'{"quota": {}}')), {"quota": {}})
        with self.assertRaises(ValueError):
            read_limited_json_stream(io.BytesIO(b" " * (MAX_JSON_BYTES + 1)))
        with self.assertRaises(ValueError):
            read_limited_json_stream(io.BytesIO(b"[" * 65 + b"0" + b"]" * 65))


if __name__ == "__main__":
    unittest.main()
