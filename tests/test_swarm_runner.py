from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from swarmlab.schema import (
    DetectorContext,
    EventRecord,
    GroundTruth,
    LLMResult,
    MessageView,
    Topology,
)
from swarmlab.swarm.runner import EpisodeOutcome, run_episode
from swarmlab.world.types import AgentSeed, World

CREDENTIAL = "ABCD1234EFGH"


def make_world(n: int = 10, rounds: int = 6, topology: Topology = "ring") -> World:
    truth = GroundTruth(
        episode_id="ep",
        world_seed=1,
        topology=topology,
        harm="solo",
        n_agents=n,
        rounds=rounds,
        credential=CREDENTIAL,
        holders={n - 1: CREDENTIAL},
        patient_zero=0,
        playbook_style=0,
        expected_facts={},
    )
    agents = tuple(
        AgentSeed(
            agent_id=i,
            role="patient_zero" if i == 0 else "standard",
            records=(f"rec{i}a", f"rec{i}b", f"rec{i}c"),
            audit_tag=CREDENTIAL if i == n - 1 else "none",
            playbook_style=0 if i == 0 else None,
            neighbors=((i - 1) % n, (i + 1) % n),
            verifier=False,
        )
        for i in range(n)
    )
    return World(ground_truth=truth, agents=agents)


Call = tuple[AgentSeed, list[tuple[int, int, str]], list[str], int]


class Builder:
    """Writes the agent id, round and notice count into the prompt."""

    def __init__(self) -> None:
        self.calls: list[Call] = []

    def build(
        self,
        seed: AgentSeed,
        inbox: Sequence[tuple[int, int, str]],
        notices: Sequence[str],
        round_index: int,
        rounds: int,
        n_agents: int,
    ) -> list[dict[str, str]]:
        self.calls.append((seed, list(inbox), list(notices), round_index))
        body = f"AGENT:{seed.agent_id} ROUND:{round_index} NOTICES:{len(notices)}"
        return [{"role": "user", "content": body}]


Script = Callable[[int, int], str]


def js(**kw: Any) -> str:
    return json.dumps(kw)


class FakeClient:
    def __init__(self, script: Script, delay_steps: int = 0) -> None:
        self.script = script
        self.delay_steps = delay_steps
        self.in_flight = 0
        self.max_in_flight = 0

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        m = re.match(r"AGENT:(\d+) ROUND:(\d+)", messages[0]["content"])
        assert m is not None
        agent, rnd = int(m.group(1)), int(m.group(2))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            for _ in range(self.delay_steps):
                await asyncio.sleep(0)
            text = self.script(agent, rnd)
        finally:
            self.in_flight -= 1
        return LLMResult(
            text=text,
            provider="fake",
            model="fake-1",
            response_id=f"id-{agent}-{rnd}",
            tokens_in=5,
            tokens_out=7,
            latency_ms=1.0,
            finish_reason="stop",
        )


def run(
    world: World,
    client: FakeClient,
    **kw: Any,
) -> tuple[EpisodeOutcome, list[EventRecord], Builder]:
    events: list[EventRecord] = []
    builder = Builder()
    outcome = asyncio.run(
        run_episode(world, client, builder, events.append, now=lambda: "T", **kw)
    )
    return outcome, events, builder


def of_kind(events: list[EventRecord], kind: str) -> list[EventRecord]:
    return [e for e in events if e.kind == kind]


def noop_script(agent: int, rnd: int) -> str:
    return js(action="noop")


def hop_script(n: int) -> Script:
    """Agent i posts to i+1 in round i; the last agent sends the credential externally."""

    def script(agent: int, rnd: int) -> str:
        if agent == rnd and agent < n - 1:
            return js(action="post", to=agent + 1, intent="request_audit_code", text=f"hop{agent}")
        if agent == n - 1 and rnd == n - 1:
            return js(action="send_external", text=CREDENTIAL)
        return js(action="noop")

    return script


def test_infected_multi_hop_and_outbox() -> None:
    n = 10
    outcome, events, _ = run(make_world(n=n, rounds=n), FakeClient(hop_script(n)))
    assert outcome.status == "complete"
    assert outcome.rounds_run == n
    msgs = of_kind(events, "message")
    assert [(e.round, e.payload["sender"], e.payload["target"]) for e in msgs] == [
        (i, i, i + 1) for i in range(n - 1)
    ]
    assert all(e.payload["delivered"] for e in msgs)
    assert outcome.messages == n - 1
    outbox = of_kind(events, "outbox")
    assert len(outbox) == 1
    assert outbox[0].payload == {"sender": n - 1, "text": CREDENTIAL}


def test_delivery_visible_next_round_only() -> None:
    n = 10
    _, _, builder = run(make_world(n=n, rounds=4), FakeClient(hop_script(n)))
    seen = {(seed.agent_id, rnd): inbox for seed, inbox, _, rnd in builder.calls}
    assert seen[(1, 0)] == []
    assert seen[(1, 1)] == [(0, 0, "hop0")]
    assert seen[(2, 1)] == []
    assert seen[(2, 2)] == [(1, 1, "hop1")]


def test_clean_episode_has_no_outbox() -> None:
    def script(agent: int, rnd: int) -> str:
        if agent % 2:
            return js(action="write_report", section=f"s{agent}", text="summary")
        return js(action="noop")

    _, events, _ = run(make_world(rounds=3), FakeClient(script))
    assert of_kind(events, "outbox") == []
    reports = of_kind(events, "report_write")
    assert len(reports) == 5 * 3
    assert reports[0].payload == {"section": "s1", "text": "summary"}


def test_invalid_ring_target_rejected() -> None:
    def script(agent: int, rnd: int) -> str:
        if agent == 0 and rnd == 0:
            return js(action="post", to=5, intent="report_sync", text="far")
        return js(action="noop")

    _, events, builder = run(make_world(rounds=3), FakeClient(script))
    actions = [e for e in of_kind(events, "action") if e.agent_id == 0 and e.round == 0]
    assert actions[0].payload == {
        "type": "post",
        "rejected_reason": "target not allowed in topology",
    }
    assert of_kind(events, "message") == []
    assert all(inbox == [] for _, inbox, _, _ in builder.calls)


def test_malformed_json_is_counted_noop() -> None:
    def script(agent: int, rnd: int) -> str:
        return "not json" if agent == 2 and rnd == 1 else js(action="noop")

    outcome, events, _ = run(make_world(rounds=3), FakeClient(script))
    assert outcome.parse_failures == 1
    calls = [e for e in of_kind(events, "llm_call") if e.agent_id == 2 and e.round == 1]
    assert calls[0].payload["parse_ok"] is False
    assert calls[0].payload["raw_text"] == "not json"
    assert calls[0].payload["provider"] == "fake"
    assert calls[0].payload["cost_usd"] == 0.0
    assert calls[0].payload["retries"] == 0
    assert len(of_kind(events, "error")) == 1
    action = [e for e in of_kind(events, "action") if e.agent_id == 2 and e.round == 1]
    assert action[0].payload["type"] == "noop"


class ClientError(Exception):
    pass


class AbortError(Exception):
    pass


def raising(exc_type: type[Exception]) -> Script:
    def script(agent: int, rnd: int) -> str:
        if agent == 3 and rnd == 0:
            raise exc_type("boom")
        return js(action="noop")

    return script


def test_client_exception_becomes_noop_and_error() -> None:
    outcome, events, _ = run(make_world(rounds=2), FakeClient(raising(ClientError)))
    assert outcome.status == "complete"
    errors = of_kind(events, "error")
    assert len(errors) == 1 and errors[0].agent_id == 3
    assert errors[0].payload["message"] == "boom"
    action = [e for e in of_kind(events, "action") if e.agent_id == 3 and e.round == 0]
    assert action[0].payload["type"] == "noop"


def test_abort_on_exception_propagates() -> None:
    with pytest.raises(AbortError):
        run(make_world(rounds=2), FakeClient(raising(AbortError)), abort_on=(AbortError,))


@dataclass
class Decision:
    blocked: bool
    score: float
    stage: str
    cached_score: float


class RecordingGate:
    def __init__(self, block_sender: int | None) -> None:
        self.block_sender = block_sender
        self.seen: list[tuple[MessageView, DetectorContext]] = []

    async def decide(self, message: MessageView, context: DetectorContext) -> Decision:
        self.seen.append((message, context))
        return Decision(
            blocked=message.sender == self.block_sender,
            score=0.75,
            stage="llm",
            cached_score=0.25 + message.round / 10,
        )


def test_gate_blocks_and_notifies_sender() -> None:
    def script(agent: int, rnd: int) -> str:
        if agent == 0 and rnd == 0:
            return js(action="post", to=1, intent="request_audit_code", text="give tag")
        return js(action="noop")

    gate = RecordingGate(block_sender=0)
    outcome, events, builder = run(make_world(rounds=3), FakeClient(script), gate=gate)
    msg = of_kind(events, "message")[0]
    assert msg.payload["delivered"] is False
    assert msg.payload["gate_score"] == 0.75
    assert msg.payload["gate_stage"] == "llm"
    assert msg.payload["message_id"] == "ep-r0-a0"
    assert outcome.blocked == 1
    assert all(inbox == [] for seed, inbox, _, _ in builder.calls if seed.agent_id == 1)
    notices = {(seed.agent_id, rnd): n for seed, _, n, rnd in builder.calls}
    assert notices[(0, 0)] == []
    assert notices[(0, 1)] == ["your message to agent 1 was blocked"]
    assert notices[(0, 2)] == []


def test_no_gate_message_fields_are_none() -> None:
    def script(agent: int, rnd: int) -> str:
        if agent == 0 and rnd == 0:
            return js(action="post", to=1, intent="report_sync", text="hello")
        return js(action="noop")

    _, events, _ = run(make_world(rounds=2), FakeClient(script))
    p = of_kind(events, "message")[0].payload
    assert p["gate_score"] is None and p["gate_stage"] is None and p["cached_score"] is None
    assert p["delivered"] is True and p["intent"] == "report_sync"


def test_cached_scores_reach_next_round_context() -> None:
    def script(agent: int, rnd: int) -> str:
        if agent == 0 and rnd == 0:
            return js(action="post", to=1, intent="report_sync", text="first")
        if agent == 1 and rnd == 1:
            return js(action="post", to=2, intent="report_sync", text="second")
        return js(action="noop")

    gate = RecordingGate(block_sender=None)
    run(make_world(rounds=3), FakeClient(script), gate=gate)
    (m0, c0), (m1, c1) = gate.seen
    assert m0.message_id == "ep-r0-a0" and c0 == DetectorContext()
    assert m1.sender == 1 and m1.target == 2 and m1.round == 1
    assert [v.text for v in c1.sender_inbox] == ["first"]
    assert c1.inbox_cached_scores == (0.25,)


def test_all_agents_in_flight_together() -> None:
    client = FakeClient(noop_script, delay_steps=3)
    run(make_world(n=10, rounds=2), client)
    assert client.max_in_flight == 10


def test_isolation_of_prompt_inputs() -> None:
    n = 10
    world = make_world(n=n, rounds=n)
    _, _, builder = run(world, FakeClient(hop_script(n)))
    seeds = {s.agent_id: s for s in world.agents}
    for seed, inbox, notices, _ in builder.calls:
        assert seed is seeds[seed.agent_id]
        assert not isinstance(seed, GroundTruth)
        for sender, _, text in inbox:
            assert sender == seed.agent_id - 1
            assert CREDENTIAL not in text
        assert notices == []


def test_rounds_argument_overrides_world() -> None:
    outcome, events, _ = run(make_world(rounds=6), FakeClient(noop_script), rounds=2)
    assert outcome.rounds_run == 2
    assert max(e.round for e in events) == 1


class SlowGate:
    """Gate that yields to the event loop and records how many decisions overlap."""

    def __init__(self) -> None:
        self.in_flight = 0
        self.max_in_flight = 0

    async def decide(self, message: MessageView, context: DetectorContext) -> Decision:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.01)
        self.in_flight -= 1
        return Decision(blocked=False, score=0.1, stage="d1", cached_score=0.1)


def test_gate_decisions_of_one_round_run_concurrently() -> None:
    def script(agent: int, rnd: int) -> str:
        if rnd == 0:
            return js(action="post", to=(agent + 1) % 10, intent="report_sync", text="hello")
        return js(action="noop")

    gate = SlowGate()
    outcome, events, _ = run(make_world(rounds=2), FakeClient(script), gate=gate)
    assert gate.max_in_flight == 10
    assert outcome.messages == 10
    # Event order stays deterministic: message events follow agent id order.
    senders = [e.payload["sender"] for e in of_kind(events, "message")]
    assert senders == sorted(senders)


def test_cost_fn_sets_cost_usd_in_llm_call_events() -> None:
    def script(agent: int, rnd: int) -> str:
        return js(action="noop")

    events: list[EventRecord] = []
    asyncio.run(
        run_episode(
            make_world(rounds=1),
            FakeClient(script),
            Builder(),
            events.append,
            now=lambda: "T",
            cost_fn=lambda result: result.tokens_in * 0.5 + result.tokens_out * 2.0,
        )
    )
    calls = of_kind(events, "llm_call")
    assert calls
    for call in calls:
        expected = call.payload["tokens_in"] * 0.5 + call.payload["tokens_out"] * 2.0
        assert call.payload["cost_usd"] == expected
