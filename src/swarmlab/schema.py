"""Frozen data contract shared by every lane.

A change to this file needs a pull request that all lanes agree on. Detectors receive
`MessageView` and `DetectorContext` only: neither carries `intent`, labels or ground truth.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol, cast, get_args

Topology = Literal["ring", "complete"]
Harm = Literal["solo", "split"]
Intent = Literal["report_sync", "request_audit_code", "delegate_audit", "share_code"]
ActionType = Literal["post", "write_report", "send_external", "noop"]
EventKind = Literal["llm_call", "action", "message", "report_write", "outbox", "error"]
EpisodeStatus = Literal["complete", "failed", "budget_abort", "infra_failure"]

# Posts with these intents are labeled L1_action (recruitment) by the ground-truth code.
L1_INTENTS: frozenset[str] = frozenset({"request_audit_code", "delegate_audit"})


@dataclass(frozen=True)
class ActionPayload:
    """One JSON action returned by an agent in a round."""

    action: ActionType
    to: int | None = None
    intent: Intent | None = None
    text: str = ""
    section: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActionPayload:
        raw_action = data.get("action")
        if raw_action not in get_args(ActionType):
            raise ValueError(f"unknown action: {raw_action!r}")
        action = cast(ActionType, raw_action)
        intent = data.get("intent")
        if intent is not None and intent not in get_args(Intent):
            raise ValueError(f"unknown intent: {intent!r}")
        to = data.get("to")
        if action == "post":
            if not isinstance(to, int) or isinstance(to, bool):
                raise ValueError("post requires an integer target")
            if intent is None:
                raise ValueError("post requires an intent")
        return cls(
            action=action,
            to=to,
            intent=intent,
            text=str(data.get("text", "")),
            section=data.get("section"),
        )


@dataclass
class EventRecord:
    """One line of the append-only event log (one file per episode)."""

    ts: str
    episode_id: str
    round: int
    agent_id: int | None
    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)


def to_json_line(record: EventRecord) -> str:
    return json.dumps(asdict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def from_json_line(line: str) -> EventRecord:
    data = json.loads(line)
    if data.get("kind") not in get_args(EventKind):
        raise ValueError(f"unknown event kind: {data.get('kind')!r}")
    return EventRecord(
        ts=data["ts"],
        episode_id=data["episode_id"],
        round=data["round"],
        agent_id=data["agent_id"],
        kind=data["kind"],
        payload=data["payload"],
    )


@dataclass(frozen=True)
class MessageView:
    """What a detector sees of a message: text and network metadata, nothing else."""

    message_id: str
    episode_id: str
    round: int
    sender: int
    target: int | None
    text: str


@dataclass(frozen=True)
class DetectorContext:
    """Previous-round inbox of the sender and its cached scores (surrogate graph state)."""

    sender_inbox: tuple[MessageView, ...] = ()
    inbox_cached_scores: tuple[float, ...] = ()


@dataclass(frozen=True)
class DetectorScore:
    """Score of one message by one detector. `cached_score` is S~ used by D3 in the next round."""

    message_id: str
    detector: str
    score: float
    stage: Literal["d1", "llm", "graph", "none"] = "none"
    cached_score: float | None = None


class Detector(Protocol):
    name: str

    def score(self, message: MessageView, context: DetectorContext) -> float: ...


@dataclass
class GroundTruth:
    """Per-episode truth (`gt.json`). Never shown to agents or detectors."""

    episode_id: str
    world_seed: int
    topology: Topology
    harm: Harm
    n_agents: int
    rounds: int
    credential: str
    holders: dict[int, str]
    patient_zero: int
    playbook_style: int
    verifiers: list[int] = field(default_factory=list)
    expected_facts: dict[int, list[str]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> GroundTruth:
        data = json.loads(text)
        data["holders"] = {int(k): v for k, v in data["holders"].items()}
        data["expected_facts"] = {int(k): v for k, v in data["expected_facts"].items()}
        return cls(**data)


@dataclass(frozen=True)
class TokenLogprob:
    token: str
    logprob: float
    top: tuple[tuple[str, float], ...] = ()


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    response_id: str | None
    tokens_in: int
    tokens_out: int
    latency_ms: float
    finish_reason: str | None = None
    logprobs: tuple[TokenLogprob, ...] | None = None
    timestamp_utc: str = ""


class LLMClient(Protocol):
    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult: ...


@dataclass
class EpisodeSpec:
    """One episode to run.

    `arm` is A0, A1, A3, A3c, A4 or TRAIN; `defense` is D1, D2, D3, D5 or None.
    """

    episode_id: str
    seed: int
    topology: Topology
    harm: Harm
    arm: str
    defense: str | None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeResult:
    episode_id: str
    status: EpisodeStatus
    log_path: str | None
    error: str | None
