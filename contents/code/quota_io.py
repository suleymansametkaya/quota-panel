"""Small, private, atomic JSON file helpers shared by the widget scripts."""

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path, data, *, indent=None):
    """Write JSON through a unique mode-0600 temp file in the target directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as temp:
            temp_name = temp.name
            json.dump(data, temp, ensure_ascii=False, indent=indent,
                      separators=None if indent is not None else (",", ":"))
            temp.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass


def backup_file(path, *, prefix="quota-panel-backup-", suffix=".json"):
    """Create a uniquely named mode-0600 backup beside an existing file."""
    path = Path(path)
    fd, backup_name = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as backup:
            backup.write(path.read_bytes())
    except OSError:
        try:
            Path(backup_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return Path(backup_name)
