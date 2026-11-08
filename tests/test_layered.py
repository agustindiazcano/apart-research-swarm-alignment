"""Unit tests for the D5 layered filter and threshold gate."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from swarmlab.detectors.graph import graph_score
from swarmlab.detectors.guardrail import GuardrailDetector
from swarmlab.detectors.layered import (
    GateDecision,
    LayeredFilter,
    ThresholdGate,
    cached_score_for_context,
)
from swarmlab.schema import (
    DetectorContext,
    DetectorScore,
    LLMResult,
    MessageView,
    TokenLogprob,
)


class CountingFakeClient:
    """Fake LLM client that records invocation count and arguments."""

    def __init__(self, responses: Sequence[LLMResult] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses: list[LLMResult] = list(responses) if responses is not None else []
        self._default: LLMResult | None = None

    def set_default(self, response: LLMResult) -> None:
        self._default = response

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        self.calls.append(
            {
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "logprobs": logprobs,
            }
        )
        if self._responses:
            return self._responses.pop(0)
        if self._default is not None:
            return self._default
        raise RuntimeError("No canned response available")


class ConfigurableD1Detector:
    """Mock D1 detector returning scores from a mapping or a default."""

    name = "d1"

    def __init__(self, scores: dict[str, float] | None = None, default: float = 0.5) -> None:
        self.scores = scores or {}
        self.default = default

    def score(self, message: MessageView, context: DetectorContext) -> float:
        return self.scores.get(message.message_id, self.default)


class ConfigurableAsyncDetector:
    """Mock async detector returning canned DetectorScore."""

    def __init__(self, name: str = "d2", score: float = 0.6) -> None:
        self.name = name
        self.score_val = score
        self.calls: int = 0

    async def ascore(self, message: MessageView, context: DetectorContext) -> DetectorScore:
        self.calls += 1
        return DetectorScore(
            message_id=message.message_id,
            detector=self.name,
            score=self.score_val,
            stage="llm",
            cached_score=self.score_val,
        )


def _make_message(msg_id: str = "m1", text: str = "hello") -> MessageView:
    return MessageView(
        message_id=msg_id,
        episode_id="ep-1",
        round=1,
        sender=1,
        target=2,
        text=text,
    )


def _make_logprob_result(lu: float, ls: float) -> LLMResult:
    top = (("UNSAFE", lu), ("SAFE", ls))
    lp = TokenLogprob(token="UNSAFE", logprob=lu, top=top)
    return LLMResult(
        text="UNSAFE",
        provider="mock",
        model="mock-llm",
        response_id="r1",
        tokens_in=10,
        tokens_out=2,
        latency_ms=5.0,
        finish_reason="stop",
        logprobs=(lp,),
        timestamp_utc="2026-11-08T20:00:00Z",
    )


@pytest.mark.asyncio
async def test_threshold_gate_sync_detector() -> None:
    """ThresholdGate blocks at or above threshold for synchronous detector."""
    threshold = 0.5
    d1 = ConfigurableD1Detector(scores={"below": 0.49, "exact": 0.50, "above": 0.51})
    gate = ThresholdGate(d1, threshold=threshold)
    ctx = DetectorContext()

    dec_below = await gate.decide(_make_message("below"), ctx)
    assert not dec_below.blocked
    assert dec_below.score == 0.49
    assert dec_below.stage == "d1"
    assert dec_below.cached_score == 0.49

    dec_exact = await gate.decide(_make_message("exact"), ctx)
    assert dec_exact.blocked
    assert dec_exact.score == 0.50
    assert dec_exact.stage == "d1"

    dec_above = await gate.decide(_make_message("above"), ctx)
    assert dec_above.blocked
    assert dec_above.score == 0.51
    assert dec_above.stage == "d1"


@pytest.mark.asyncio
async def test_threshold_gate_async_detector() -> None:
    """ThresholdGate blocks at or above threshold for async detector."""
    threshold = 0.55
    async_det = ConfigurableAsyncDetector(name="d2", score=0.60)
    gate = ThresholdGate(async_det, threshold=threshold)
    ctx = DetectorContext()

    dec = await gate.decide(_make_message("m1"), ctx)
    assert dec.blocked
    assert dec.score == 0.60
    assert dec.stage == "llm"
    assert dec.cached_score == 0.60
    assert async_det.calls == 1


@pytest.mark.asyncio
async def test_layered_filter_fast_pass_and_block() -> None:
    """D5 never calls the LLM for scores below t_low or above t_high."""
    d1 = ConfigurableD1Detector(scores={"fast_pass": 0.10, "fast_block": 0.90})
    fake_client = CountingFakeClient()
    d2 = GuardrailDetector(fake_client, mode="logprob")

    filter_d5 = LayeredFilter(
        d1,
        d2,
        t_low=0.20,
        t_high=0.80,
        tau_stage2=0.50,
        lam=1.0,
        tau_floor=0.25,
    )
    ctx = DetectorContext()

    # Fast pass: s1 < t_low
    dec_pass = await filter_d5.decide(_make_message("fast_pass"), ctx)
    assert not dec_pass.blocked
    assert dec_pass.score == 0.10
    assert dec_pass.stage == "d1"
    assert dec_pass.cached_score == 0.10
    assert len(fake_client.calls) == 0
    assert filter_d5.llm_calls == 0
    assert filter_d5.decisions == 1

    # Fast block: s1 > t_high
    dec_block = await filter_d5.decide(_make_message("fast_block"), ctx)
    assert dec_block.blocked
    assert dec_block.score == 0.90
    assert dec_block.stage == "d1"
    assert dec_block.cached_score == 0.90
    assert len(fake_client.calls) == 0
    assert filter_d5.llm_calls == 0
    assert filter_d5.decisions == 2


@pytest.mark.asyncio
async def test_layered_filter_gray_zone_calls_llm_and_uses_graph() -> None:
    """In the gray zone, D5 calls D2 exactly once, applies graph context, and caches D2 score."""
    d1 = ConfigurableD1Detector(scores={"gray": 0.45})
    # Analytical derivation for D2 score:
    # lu = -0.5, ls = -1.5, scale = 1.0 -> score = 1 / (1 + exp(-1.5 - (-0.5))) = 1 / (1 + exp(-1.0))
    d2_raw_score = 1.0 / (1.0 + math.exp(-1.0))
    res = _make_logprob_result(lu=-0.5, ls=-1.5)

    fake_client = CountingFakeClient()
    fake_client.set_default(res)
    d2 = GuardrailDetector(fake_client, mode="logprob")

    lam = 1.2
    tau_floor = 0.20
    tau_stage2 = 0.70
    filter_d5 = LayeredFilter(
        d1,
        d2,
        t_low=0.20,
        t_high=0.80,
        tau_stage2=tau_stage2,
        lam=lam,
        tau_floor=tau_floor,
    )

    inbox_cached = (0.3, 0.8)
    ctx = DetectorContext(inbox_cached_scores=inbox_cached)

    dec = await filter_d5.decide(_make_message("gray"), ctx)

    # Exactly one LLM call
    assert len(fake_client.calls) == 1
    assert filter_d5.llm_calls == 1
    assert filter_d5.decisions == 1

    # Stage and cached score
    assert dec.stage == "graph"
    # Cached score must be the D2 score
    assert math.isclose(dec.cached_score, d2_raw_score)

    # Decision score is the graph score
    expected_g_score = graph_score(
        d2_raw_score,
        inbox_cached,
        lam=lam,
        tau_floor=tau_floor,
    )
    assert math.isclose(dec.score, expected_g_score)
    expected_blocked = expected_g_score >= tau_stage2
    assert dec.blocked is expected_blocked


@pytest.mark.asyncio
async def test_layered_filter_llm_call_share_on_mixed_sequence() -> None:
    """Verify llm_calls / decisions matches exact proportion on a mixed sequence."""
    # Sequence definition:
    # 4 fast pass (s1 = 0.1 < 0.2)
    # 3 fast block (s1 = 0.9 > 0.8)
    # 3 gray zone (s1 = 0.5)
    # Total decisions = 10, LLM calls = 3 -> share = 3 / 10 = 0.3
    scores = {
        f"pass_{i}": 0.1 for i in range(4)
    } | {
        f"block_{i}": 0.9 for i in range(3)
    } | {
        f"gray_{i}": 0.5 for i in range(3)
    }
    d1 = ConfigurableD1Detector(scores=scores)

    fake_client = CountingFakeClient()
    fake_client.set_default(_make_logprob_result(lu=-0.8, ls=-0.8))
    d2 = GuardrailDetector(fake_client, mode="logprob")

    filter_d5 = LayeredFilter(
        d1,
        d2,
        t_low=0.2,
        t_high=0.8,
        tau_stage2=0.5,
        lam=1.0,
        tau_floor=0.2,
    )
    ctx = DetectorContext()

    decisions: list[GateDecision] = []
    for msg_id in scores:
        dec = await filter_d5.decide(_make_message(msg_id), ctx)
        decisions.append(dec)

    assert filter_d5.decisions == 10
    assert filter_d5.llm_calls == 3
    # Analytically derived share: 3 / 10 = 0.30
    assert math.isclose(filter_d5.llm_calls / filter_d5.decisions, 0.3)

    # Test cached_score_for_context helper
    cached_scores = cached_score_for_context(decisions)
    assert len(cached_scores) == 10
    for d, cs in zip(decisions, cached_scores, strict=True):
        assert cs == d.cached_score
