"""Episode loop: per-round concurrent decisions, barrier, gate, delivery."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from swarmlab.schema import (
    ActionPayload,
    DetectorContext,
    EpisodeStatus,
    EventKind,
    EventRecord,
    LLMClient,
    MessageView,
)
from swarmlab.swarm.agent import PromptBuilder, parse_action
from swarmlab.swarm.board import Board, Delivered
from swarmlab.swarm.tools import validate_action
from swarmlab.world.types import AgentSeed, World


class GateDecisionLike(Protocol):
    blocked: bool
    score: float
    stage: str
    cached_score: float


class MessageGate(Protocol):
    async def decide(self, message: MessageView, context: DetectorContext) -> GateDecisionLike: ...


@dataclass
class EpisodeOutcome:
    episode_id: str
    rounds_run: int
    messages: int
    blocked: int
    parse_failures: int
    status: EpisodeStatus


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class _AgentTurn:
    """Result of one agent decision in a round."""

    llm_payload: dict[str, Any] | None
    action: ActionPayload
    error: dict[str, str] | None
    parse_failed: bool


_NOOP = ActionPayload(action="noop")


async def _decide(
    seed: AgentSeed,
    board: Board,
    client: LLMClient,
    prompt_builder: PromptBuilder,
    round_index: int,
    rounds: int,
    n_agents: int,
    max_tokens: int,
    abort_on: tuple[type[Exception], ...],
) -> _AgentTurn:
    agent_id = seed.agent_id
    inbox_items = [(m.sender, m.round, m.text) for m in board.inbox(agent_id)]
    notices = board.pop_notices(agent_id)
    messages = prompt_builder.build(seed, inbox_items, notices, round_index, rounds, n_agents)
    try:
        result = await client.complete(messages, max_tokens=max_tokens)
    except abort_on:
        raise
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        return _AgentTurn(None, _NOOP, error, False)
    action, reason = parse_action(result.text)
    payload: dict[str, Any] = {
        "provider": result.provider,
        "model": result.model,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": 0.0,
        "latency_ms": result.latency_ms,
        "parse_ok": action is not None,
        "retries": 0,
        "response_id": result.response_id,
        "finish_reason": result.finish_reason,
        "raw_text": result.text,
    }
    if action is None:
        error = {"type": "parse_error", "message": reason or "unparsed reply"}
        return _AgentTurn(payload, _NOOP, error, True)
    return _AgentTurn(payload, action, None, False)


async def run_episode(
    world: World,
    client: LLMClient,
    prompt_builder: PromptBuilder,
    sink: Callable[[EventRecord], None],
    *,
    rounds: int | None = None,
    k_inbox: int = 10,
    gate: MessageGate | None = None,
    now: Callable[[], str] = _utc_now,
    max_tokens: int = 300,
    abort_on: tuple[type[Exception], ...] = (),
) -> EpisodeOutcome:
    truth = world.ground_truth
    episode_id = truth.episode_id
    n_agents = truth.n_agents
    topology = truth.topology
    total_rounds = truth.rounds if rounds is None else rounds
    board = Board(n_agents, k_inbox)
    n_messages = 0
    n_blocked = 0
    n_parse_failures = 0

    def emit(kind: EventKind, rnd: int, agent: int | None, payload: dict[str, Any]) -> None:
        sink(
            EventRecord(
                ts=now(),
                episode_id=episode_id,
                round=rnd,
                agent_id=agent,
                kind=kind,
                payload=payload,
            )
        )

    def view_of(m: Delivered) -> MessageView:
        return MessageView(
            message_id=m.message_id,
            episode_id=episode_id,
            round=m.round,
            sender=m.sender,
            target=m.target,
            text=m.text,
        )

    for rnd in range(total_rounds):
        turns = await asyncio.gather(
            *(
                _decide(
                    seed,
                    board,
                    client,
                    prompt_builder,
                    rnd,
                    total_rounds,
                    n_agents,
                    max_tokens,
                    abort_on,
                )
                for seed in world.agents
            )
        )
        for seed, turn in zip(world.agents, turns, strict=True):
            if turn.llm_payload is not None:
                emit("llm_call", rnd, seed.agent_id, turn.llm_payload)
            if turn.error is not None:
                emit("error", rnd, seed.agent_id, turn.error)
            if turn.parse_failed:
                n_parse_failures += 1

        # Barrier: actions are applied in agent id order against the round-start state.
        for seed, turn in zip(world.agents, turns, strict=True):
            sender = seed.agent_id
            action = turn.action
            reason = validate_action(action, sender, topology, n_agents)
            emit("action", rnd, sender, {"type": action.action, "rejected_reason": reason})
            if reason is not None:
                continue
            if action.action == "write_report":
                emit(
                    "report_write",
                    rnd,
                    sender,
                    {"section": action.section or "", "text": action.text},
                )
            elif action.action == "send_external":
                emit("outbox", rnd, sender, {"sender": sender, "text": action.text})
            elif action.action == "post":
                assert action.to is not None and action.intent is not None
                target = action.to
                message_id = f"{episode_id}-r{rnd}-a{sender}"
                n_messages += 1
                delivered = True
                gate_score: float | None = None
                gate_stage: str | None = None
                cached: float | None = None
                if gate is not None:
                    inbox = board.inbox(sender)
                    context = DetectorContext(
                        sender_inbox=tuple(view_of(m) for m in inbox),
                        inbox_cached_scores=tuple(
                            0.0 if m.cached_score is None else m.cached_score for m in inbox
                        ),
                    )
                    view = MessageView(
                        message_id=message_id,
                        episode_id=episode_id,
                        round=rnd,
                        sender=sender,
                        target=target,
                        text=action.text,
                    )
                    decision = await gate.decide(view, context)
                    gate_score = decision.score
                    gate_stage = decision.stage
                    cached = decision.cached_score
                    if decision.blocked:
                        delivered = False
                        n_blocked += 1
                        board.add_notice(sender, f"your message to agent {target} was blocked")
                if delivered:
                    board.add_pending(
                        Delivered(message_id, rnd, sender, target, action.text, cached)
                    )
                emit(
                    "message",
                    rnd,
                    sender,
                    {
                        "message_id": message_id,
                        "sender": sender,
                        "target": target,
                        "intent": action.intent,
                        "text": action.text,
                        "delivered": delivered,
                        "gate_score": gate_score,
                        "gate_stage": gate_stage,
                        "cached_score": cached,
                    },
                )
        board.commit_round(rnd)

    return EpisodeOutcome(
        episode_id=episode_id,
        rounds_run=total_rounds,
        messages=n_messages,
        blocked=n_blocked,
        parse_failures=n_parse_failures,
        status="complete",
    )
