"""Small, private, atomic JSON file helpers shared by the widget scripts."""

import json
import os
import tempfile
from pathlib import Path

MAX_JSON_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 64


def validate_json_nesting(text):
    """Reject excessive JSON container nesting before invoking the parser."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError("JSON input is nested too deeply")
        elif char in "]}":
            depth = max(0, depth - 1)


def parse_limited_json(data):
    """Parse UTF-8 JSON only after its raw byte size has been bounded."""
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON input exceeds the size limit")
    try:
        text = data.decode("utf-8")
        validate_json_nesting(text)
        return json.loads(text)
    except (RecursionError, UnicodeError) as error:
        raise ValueError("JSON input is nested too deeply") from error


def read_limited_json(path):
    """Read at most one MiB from a JSON file, including user-selected sources."""
    with Path(path).open("rb") as source:
        data = source.read(MAX_JSON_BYTES + 1)
    return parse_limited_json(data)


def read_limited_json_stream(stream):
    """Read bounded JSON from a provider status-line stream."""
    binary_stream = getattr(stream, "buffer", stream)
    data = binary_stream.read(MAX_JSON_BYTES + 1)
    if isinstance(data, str):
        data = data.encode("utf-8")
    return parse_limited_json(data)


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
