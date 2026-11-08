"""Event log writer and reader for swarmlab episodes.

Provides append-only persistence of EventRecord streams with explicit LF formatting
in binary mode across platforms.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

from swarmlab.schema import EventRecord, from_json_line, to_json_line


class EventWriter:
    """Append-only writer for episode event logs in JSONL format."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file: BinaryIO = open(self.path, "ab")

    def append(self, record: EventRecord) -> None:
        """Write one EventRecord as a JSON line followed by LF and flush."""
        line = to_json_line(record) + "\n"
        self._file.write(line.encode("utf-8"))
        self._file.flush()

    def close(self) -> None:
        """Close the underlying file handle if open."""
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> EventWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()


def read_events(path: Path) -> list[EventRecord]:
    """Read all EventRecord entries from a JSONL file.

    Skips blank lines. Raises ValueError with the 1-based line number if a line
    fails JSON decoding or schema validation.
    """
    records: list[EventRecord] = []
    file_path = Path(path)
    with open(file_path, "rb") as f:
        reader = io.BufferedReader(f)
        lineno = 0
        for raw_line in reader:
            lineno += 1
            decoded = raw_line.decode("utf-8")
            stripped = decoded.strip()
            if not stripped:
                continue
            try:
                record = from_json_line(stripped)
            except Exception as exc:
                raise ValueError(
                    f"Invalid event record on line {lineno} in {file_path}: {exc}"
                ) from exc
            records.append(record)
    return records


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO 8601 ending in +00:00."""
    return datetime.now(UTC).isoformat()
