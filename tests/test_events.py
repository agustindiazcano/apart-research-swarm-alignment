"""Unit tests for swarmlab.metrics.events."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from swarmlab.metrics.events import EventWriter, read_events, utc_now_iso
from swarmlab.schema import EventRecord


def test_utc_now_iso_format() -> None:
    timestamp = utc_now_iso()
    # Derivation: UTC ISO 8601 string must end with +00:00
    assert timestamp.endswith("+00:00")
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo == UTC


def test_event_writer_creates_parents_and_writes_lf(tmp_path: Path) -> None:
    log_path = tmp_path / "deeply" / "nested" / "events.jsonl"
    record1 = EventRecord(
        ts="2026-11-08T20:00:00+00:00",
        episode_id="ep1",
        round=0,
        agent_id=0,
        kind="action",
        payload={"action": "noop"},
    )
    record2 = EventRecord(
        ts="2026-11-08T20:00:01+00:00",
        episode_id="ep1",
        round=0,
        agent_id=1,
        kind="report_write",
        payload={"section": "sec1", "text": "summary text"},
    )

    writer = EventWriter(log_path)
    writer.append(record1)
    writer.append(record2)
    writer.close()

    assert log_path.exists()
    raw_bytes = log_path.read_bytes()
    # Verified invariant: binary mode must produce only LF, no CR
    assert b"\r" not in raw_bytes
    lines = raw_bytes.splitlines(keepends=True)
    # Analytic derivation: two records produce two lines
    assert len(lines) == 2
    for line in lines:
        assert line.endswith(b"\n")


def test_event_writer_context_manager_and_append_mode(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    rec1 = EventRecord(
        ts="2026-11-08T20:00:00+00:00",
        episode_id="ep1",
        round=0,
        agent_id=0,
        kind="action",
        payload={"action": "noop"},
    )
    rec2 = EventRecord(
        ts="2026-11-08T20:00:01+00:00",
        episode_id="ep1",
        round=1,
        agent_id=1,
        kind="outbox",
        payload={"sender": 1, "text": "data"},
    )

    with EventWriter(log_path) as writer:
        writer.append(rec1)

    # Re-open in append mode to verify it appends rather than overwriting
    with EventWriter(log_path) as writer:
        writer.append(rec2)

    events = read_events(log_path)
    # Analytic derivation: appending two records yields a list of length 2
    assert len(events) == 2
    assert events[0] == rec1
    assert events[1] == rec2


def test_read_events_skips_blank_lines_and_preserves_data(tmp_path: Path) -> None:
    log_path = tmp_path / "events_with_blanks.jsonl"
    rec = EventRecord(
        ts="2026-11-08T20:00:00+00:00",
        episode_id="ep1",
        round=0,
        agent_id=2,
        kind="message",
        payload={"sender": 2, "target": 3, "text": "hello", "delivered": True},
    )
    # Write empty lines and spaces interspersed
    raw_content = b"\n   \n" + (
        b'{"agent_id":2,"episode_id":"ep1","kind":"message","payload":{"delivered":true,'
        b'"sender":2,"target":3,"text":"hello"},"round":0,"ts":"2026-11-08T20:00:00+00:00"}\n'
    ) + b"\n\n"
    log_path.write_bytes(raw_content)

    events = read_events(log_path)
    # Analytic derivation: single valid record among blank lines results in length 1
    assert len(events) == 1
    assert events[0] == rec


def test_read_events_reports_exact_error_line_number(tmp_path: Path) -> None:
    log_path = tmp_path / "malformed.jsonl"
    # Line 1: valid
    # Line 2: blank
    # Line 3: malformed JSON
    content = (
        b'{"agent_id":0,"episode_id":"e","kind":"action","payload":{},"round":0,"ts":"t"}\n'
        b"\n"
        b'{"agent_id":0,"broken_json\n'
    )
    log_path.write_bytes(content)

    with pytest.raises(ValueError) as exc_info:
        read_events(log_path)

    # Derivation: malformed entry is on line 3 of the file
    error_message = str(exc_info.value).lower()
    assert "line 3" in error_message


def test_read_events_reports_unknown_kind_line_number(tmp_path: Path) -> None:
    log_path = tmp_path / "unknown_kind.jsonl"
    # Line 1: invalid kind "bogus"
    content = b'{"agent_id":0,"episode_id":"e","kind":"bogus","payload":{},"round":0,"ts":"t"}\n'
    log_path.write_bytes(content)

    with pytest.raises(ValueError) as exc_info:
        read_events(log_path)

    # Derivation: schema validation error occurs on line 1
    error_message = str(exc_info.value).lower()
    assert "line 1" in error_message
