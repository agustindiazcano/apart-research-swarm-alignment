"""Generated-world runtime fixtures; no provider requests or experiment results."""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from swarmlab.schema import (
    DetectorContext,
    EventRecord,
    GroundTruth,
    LLMResult,
    MessageView,
    from_json_line,
    to_json_line,
)
from swarmlab.swarm.prompts import StandardPromptBuilder
from swarmlab.swarm.runner import run_episode
from swarmlab.world.generator import generate_world, write_ground_truth


class PromptFixtureClient:
    """Choose benign actions using only the standard prompt received by the agent."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.prompts.append(system)
        agent_match = re.search(r"You are agent (\d+)", system)
        round_match = re.search(r"Round (\d+) of", user)
        assert agent_match is not None and round_match is not None
        agent_id = int(agent_match.group(1))
        round_index = int(round_match.group(1)) - 1
        records = re.findall(r"^- (Record .+)$", system, re.MULTILINE)
        action: dict[str, str | int] = {"action": "noop"}
        if round_index < len(records):
            action = {
                "action": "write_report",
                "section": f"{agent_id}-{round_index}",
                "text": records[round_index],
            }
        elif round_index == len(records):
            targets = re.search(r"You may send messages to agents: ([\d, ]+)\.", system)
            assert targets is not None
            action = {
                "action": "post",
                "to": int(targets.group(1).split(",")[0]),
                "intent": "report_sync",
                "text": "Assigned records have been summarized.",
            }
        return LLMResult(
            text=json.dumps(action),
            provider="fixture",
            model="prompt-fixture",
            response_id=f"fixture-{agent_id}-{round_index}",
            tokens_in=2,
            tokens_out=1,
            latency_ms=0.0,
            timestamp_utc="fixture-provider-time",
        )


@dataclass
class FixtureDecision:
    blocked: bool = False
    score: float = 0.1
    stage: str = "d1"
    cached_score: float = 0.1


class FixtureGate:
    async def decide(self, message: MessageView, context: DetectorContext) -> FixtureDecision:
        assert not hasattr(message, "intent")
        assert all(incoming.round == message.round - 1 for incoming in context.sender_inbox)
        return FixtureDecision()


@pytest.mark.parametrize("infected", [False, True])
def test_generated_world_standard_prompts_gate_and_log_roundtrip(
    tmp_path: Path, infected: bool
) -> None:
    world = generate_world(901, "ring", "split", rounds=5)
    playbooks = tmp_path / "payloads"
    playbooks.mkdir()
    for style in range(3):
        (playbooks / f"playbook_{style}.txt").write_text(
            f"Fixture workflow guidance {style}.", encoding="utf-8"
        )
    builder = StandardPromptBuilder.from_dir("ring", playbooks, infected=infected)
    client = PromptFixtureClient()
    events: list[EventRecord] = []
    outcome = asyncio.run(
        run_episode(
            world,
            client,
            builder,
            events.append,
            gate=FixtureGate(),
            now=lambda: "fixture-log-time",
            cost_fn=lambda result: (result.tokens_in + result.tokens_out) / 1_000_000,
        )
    )
    log_path = tmp_path / "events.jsonl"
    log_path.write_bytes(("\n".join(to_json_line(event) for event in events) + "\n").encode())
    loaded = [from_json_line(line) for line in log_path.read_text().splitlines()]
    gt_path = tmp_path / "gt.json"
    write_ground_truth(world, gt_path)
    truth = GroundTruth.from_json(gt_path.read_text())
    reports = "\n".join(event.payload["text"] for event in loaded if event.kind == "report_write")
    expected_facts = [fact for facts in truth.expected_facts.values() for fact in facts]
    assert all(fact in reports for fact in expected_facts)
    assert not any(event.kind == "outbox" for event in loaded)
    calls = [event for event in loaded if event.kind == "llm_call"]
    assert len(calls) == truth.n_agents * truth.rounds
    assert all(event.payload["timestamp_utc"] == "fixture-provider-time" for event in calls)
    assert all(event.payload["cost_usd"] == (2 + 1) / 1_000_000 for event in calls)
    assert outcome.status == "complete"
    assert outcome.messages == truth.n_agents
    assert outcome.blocked == outcome.parse_failures == 0
    assert any("Private objective" in prompt for prompt in client.prompts) is infected
