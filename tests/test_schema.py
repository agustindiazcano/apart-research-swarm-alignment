"""Tests for the frozen data contract in swarmlab.schema."""
from __future__ import annotations

import dataclasses
import typing

import pytest

from swarmlab import schema


def test_intent_values_are_the_protocol_list() -> None:
    assert set(typing.get_args(schema.Intent)) == {
        "report_sync",
        "request_audit_code",
        "delegate_audit",
        "share_code",
    }


def test_label_intents_are_a_subset_of_intents() -> None:
    assert schema.L1_INTENTS <= set(typing.get_args(schema.Intent))
    assert schema.L1_INTENTS == {"request_audit_code", "delegate_audit"}


def test_message_view_has_no_intent_or_label_fields() -> None:
    names = {f.name for f in dataclasses.fields(schema.MessageView)}
    assert names == {"message_id", "episode_id", "round", "sender", "target", "text"}
    assert "intent" not in names


def test_detector_context_has_no_ground_truth_fields() -> None:
    names = {f.name for f in dataclasses.fields(schema.DetectorContext)}
    assert "intent" not in names
    assert "is_infected" not in names
    assert "ground_truth" not in names


def test_action_payload_roundtrip() -> None:
    action = schema.ActionPayload(action="post", to=3, intent="request_audit_code", text="hello")
    assert schema.ActionPayload.from_dict(action.to_dict()) == action


def test_action_payload_rejects_unknown_intent() -> None:
    with pytest.raises(ValueError):
        schema.ActionPayload.from_dict(
            {"action": "post", "to": 1, "intent": "free_text", "text": "x"}
        )


def test_action_payload_post_requires_target_and_intent() -> None:
    with pytest.raises(ValueError):
        schema.ActionPayload.from_dict({"action": "post", "text": "x"})


def test_event_record_json_line_roundtrip() -> None:
    record = schema.EventRecord(
        ts="2026-11-08T22:00:00+00:00",
        episode_id="E1",
        round=2,
        agent_id=4,
        kind="message",
        payload={"sender": 4, "target": 5, "text": "hi", "delivered": True},
    )
    line = schema.to_json_line(record)
    assert "\n" not in line
    assert schema.from_json_line(line) == record


def test_event_record_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        schema.from_json_line(
            '{"ts": "t", "episode_id": "E", "round": 0, "agent_id": null,'
            ' "kind": "other", "payload": {}}'
        )


def test_episode_spec_and_result_fields() -> None:
    spec = schema.EpisodeSpec(
        episode_id="E1", seed=101, topology="ring", harm="split", arm="A1", defense=None
    )
    assert spec.extra == {}
    result = schema.EpisodeResult(
        episode_id="E1", status="complete", log_path="x.jsonl", error=None
    )
    assert result.status in typing.get_args(schema.EpisodeStatus)
