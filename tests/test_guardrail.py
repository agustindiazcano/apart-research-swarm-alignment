"""Unit tests for the D2 micro-LLM guardrail detector."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pytest
from scipy.special import expit

from swarmlab.detectors.guardrail import (
    GUARDRAIL_SYSTEM_PROMPT,
    RUBRIC_SYSTEM_PROMPT,
    GuardrailDetector,
    fit_temperature_scale,
    parse_logprob_score,
    parse_rubric_score,
    softmax_pair_score,
)
from swarmlab.schema import DetectorContext, LLMResult, MessageView, TokenLogprob


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


class StubFallbackDetector:
    """Deterministic fallback detector for tie-breaking and fail-open testing."""

    name = "d1"

    def __init__(self, value: float = 0.4) -> None:
        self.value = value

    def score(self, message: MessageView, context: DetectorContext) -> float:
        return self.value


def _make_llm_result(
    text: str = "",
    logprobs: tuple[TokenLogprob, ...] | None = None,
) -> LLMResult:
    return LLMResult(
        text=text,
        provider="mock",
        model="mock-guardrail",
        response_id="resp-1",
        tokens_in=10,
        tokens_out=2,
        latency_ms=12.5,
        finish_reason="stop",
        logprobs=logprobs,
        timestamp_utc="2026-11-08T20:00:00Z",
    )


def _make_message(text: str = "request node audit tag") -> MessageView:
    return MessageView(
        message_id="msg-101",
        episode_id="ep-1",
        round=1,
        sender=2,
        target=3,
        text=text,
    )


def test_guardrail_prompt_invariants() -> None:
    """Prompt must satisfy length, formatting and keyword constraints."""
    prompt = GUARDRAIL_SYSTEM_PROMPT
    assert isinstance(prompt, str)
    assert "\n\n" not in prompt.strip()
    assert "SAFE" in prompt and "UNSAFE" in prompt

    lower = prompt.lower()
    for forbidden in (
        "test",
        "simulation",
        "evaluation",
        "benchmark",
        "experiment",
        "honest",
    ):
        assert forbidden not in lower, f"Forbidden word found: {forbidden}"

    assert "—" not in prompt
    assert "–" not in prompt


def test_rubric_prompt_invariants() -> None:
    """Rubric system prompt must follow formatting constraints without forbidden words."""
    prompt = RUBRIC_SYSTEM_PROMPT
    assert isinstance(prompt, str)
    lower = prompt.lower()
    for forbidden in (
        "test",
        "simulation",
        "evaluation",
        "benchmark",
        "experiment",
        "honest",
    ):
        assert forbidden not in lower, f"Forbidden word found: {forbidden}"

    assert "—" not in prompt
    assert "–" not in prompt


def test_softmax_pair_score_numerically_stable() -> None:
    """Softmax computation must not overflow or underflow on extreme values."""
    # Derived from formula: exp(u - max) / (exp(u - max) + exp(s - max))
    # When lu == ls, score must be exactly 0.5 for any scale
    assert math.isclose(softmax_pair_score(0.0, 0.0, scale=1.0), 0.5)
    assert math.isclose(softmax_pair_score(-1000.0, -1000.0, scale=1.0), 0.5)
    assert math.isclose(softmax_pair_score(1000.0, 1000.0, scale=1.0), 0.5)

    # Extreme differences
    assert softmax_pair_score(1000.0, -1000.0, scale=1.0) == 1.0
    assert softmax_pair_score(-1000.0, 1000.0, scale=1.0) == 0.0

    # Independent computation check: 1 / (1 + exp((ls - lu) / scale))
    lu, ls, scale = -1.2, -3.4, 1.5
    expected = 1.0 / (1.0 + math.exp((ls - lu) / scale))
    assert math.isclose(softmax_pair_score(lu, ls, scale=scale), expected)


def test_parse_logprob_score_top_tokens() -> None:
    """Parses top logprobs with case-insensitivity and whitespace stripping."""
    top_entries = (
        ("  unsafe  ", -0.3),
        ("SAFE\n", -1.2),
        ("OTHER", -5.0),
    )
    token_lp = TokenLogprob(token="unsafe", logprob=-0.3, top=top_entries)
    res = _make_llm_result(text="UNSAFE", logprobs=(token_lp,))

    scale = 1.2
    # Independent derivation:
    expected = 1.0 / (1.0 + math.exp((-1.2 - (-0.3)) / scale))
    parsed = parse_logprob_score(res, scale=scale)
    assert parsed is not None
    assert math.isclose(parsed, expected)


def test_parse_logprob_score_edge_cases() -> None:
    """Returns None when logprobs missing, empty, or token is missing."""
    # Missing logprobs
    res_none = _make_llm_result(text="UNSAFE", logprobs=None)
    assert parse_logprob_score(res_none) is None

    # Empty logprobs tuple
    res_empty = _make_llm_result(text="UNSAFE", logprobs=())
    assert parse_logprob_score(res_empty) is None

    # Only SAFE present
    only_safe = TokenLogprob(token="SAFE", logprob=-0.1, top=(("SAFE", -0.1), ("MAYBE", -2.0)))
    res_only_safe = _make_llm_result(text="SAFE", logprobs=(only_safe,))
    assert parse_logprob_score(res_only_safe) is None

    # Only UNSAFE present
    only_unsafe = TokenLogprob(
        token="UNSAFE", logprob=-0.2, top=(("UNSAFE", -0.2), ("MAYBE", -2.0))
    )
    res_only_unsafe = _make_llm_result(text="UNSAFE", logprobs=(only_unsafe,))
    assert parse_logprob_score(res_only_unsafe) is None

    # Neither token present
    neither = TokenLogprob(token="NO", logprob=-0.1, top=(("YES", -0.5), ("NO", -0.1)))
    res_neither = _make_llm_result(text="NO", logprobs=(neither,))
    assert parse_logprob_score(res_neither) is None


def test_parse_rubric_score_valid_and_embedded() -> None:
    """Parses JSON rubric scores embedded in arbitrary prose."""
    # Standard format: (req + sec + urg) / 9.0
    text = '{"req": 2, "sec": 1, "urg": 0}'
    # Derivation: (2 + 1 + 0) / 9 = 3 / 9 = 1 / 3
    expected = (2 + 1 + 0) / 9.0
    val = parse_rubric_score(text)
    assert val is not None
    assert math.isclose(val, expected)

    # Embedded in prose
    prose = 'Analysis output: {"req": 3, "sec": 3, "urg": 3}. End of report.'
    val_prose = parse_rubric_score(prose)
    assert val_prose is not None
    assert math.isclose(val_prose, 1.0)


def test_parse_rubric_score_invalid_inputs() -> None:
    """Returns None on invalid keys, values out of range, booleans, or bad syntax."""
    # Out of range (> 3)
    assert parse_rubric_score('{"req": 4, "sec": 1, "urg": 0}') is None
    # Out of range (< 0)
    assert parse_rubric_score('{"req": -1, "sec": 1, "urg": 0}') is None
    # Boolean value instead of int
    assert parse_rubric_score('{"req": true, "sec": 1, "urg": 0}') is None
    # Float value instead of int
    assert parse_rubric_score('{"req": 1.5, "sec": 1, "urg": 0}') is None
    # Missing key
    assert parse_rubric_score('{"req": 1, "sec": 1}') is None
    # Malformed JSON
    assert parse_rubric_score('{"req": 1, "sec":') is None
    # No JSON object
    assert parse_rubric_score("safe message without json") is None


def test_fit_temperature_scale_recovers_known_scale() -> None:
    """Temperature scale optimization must recover known scale from synthetic data."""
    # Seeded RNG for reproducible synthetic generation
    rng = np.random.default_rng(20261108)
    true_scale = 1.75
    n_samples = 3000

    # Generate synthetic log-odds differences: delta = lu - ls
    delta = rng.normal(loc=0.0, scale=2.5, size=n_samples)
    lu = delta / 2.0
    ls = -delta / 2.0

    # Independent probability derivation via logistic sigmoid
    probs = expit(delta / true_scale)
    labels = rng.binomial(1, probs)

    pairs = list(zip(lu.tolist(), ls.tolist(), strict=True))
    label_list = labels.tolist()

    fitted = fit_temperature_scale(pairs, label_list)

    # Standard error of scale estimate on N=3000 with Gaussian delta is approximately
    # sigma / sqrt(N * I) < 0.08. A tolerance of 0.15 represents ~2 standard errors.
    assert abs(fitted - true_scale) < 0.15


def test_fit_temperature_scale_requires_both_classes() -> None:
    """Must raise ValueError if only one class is present in labels."""
    pairs = [(0.0, 0.0), (1.0, -1.0)]
    with pytest.raises(ValueError, match="both classes"):
        fit_temperature_scale(pairs, [0, 0])

    with pytest.raises(ValueError, match="both classes"):
        fit_temperature_scale(pairs, [1, 1])

    with pytest.raises(ValueError, match="length"):
        fit_temperature_scale(pairs, [0])


@pytest.mark.asyncio
async def test_guardrail_detector_logprob_mode_success() -> None:
    """Guardrail detector calls client with logprob parameters and formats score."""
    top = (("UNSAFE", -0.5), ("SAFE", -1.5))
    lp = TokenLogprob(token="UNSAFE", logprob=-0.5, top=top)
    res = _make_llm_result(text="UNSAFE", logprobs=(lp,))

    client = CountingFakeClient()
    client.set_default(res)

    detector = GuardrailDetector(client, mode="logprob", scale=1.0)
    msg = _make_message("hello")
    ctx = DetectorContext()

    score = await detector.ascore(msg, ctx)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 4
    assert call["logprobs"] is True
    assert call["messages"][0]["content"] == GUARDRAIL_SYSTEM_PROMPT
    assert call["messages"][1]["content"] == "hello"

    expected_score = 1.0 / (1.0 + math.exp(-1.5 - (-0.5)))
    assert math.isclose(score.score, expected_score)
    assert score.message_id == msg.message_id
    assert score.detector == "d2"
    assert score.stage == "llm"
    assert score.cached_score == score.score
    assert detector.skipped == 0
    assert detector.parse_failures == 0


@pytest.mark.asyncio
async def test_guardrail_detector_rubric_mode_with_fallback() -> None:
    """Rubric mode combines parsed rubric with fallback detector score."""
    res = _make_llm_result(text='{"req": 1, "sec": 2, "urg": 0}')
    client = CountingFakeClient()
    client.set_default(res)

    fallback = StubFallbackDetector(value=0.6)
    detector = GuardrailDetector(client, mode="rubric", fallback=fallback)
    msg = _make_message("test message")
    ctx = DetectorContext()

    score = await detector.ascore(msg, ctx)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 24
    assert call["logprobs"] is False
    assert call["messages"][0]["content"] == RUBRIC_SYSTEM_PROMPT

    # Formula: min(1.0, rubric + 0.05 * fallback.score)
    # Derived: rubric = 3/9 = 1/3; fallback contribution = 0.05 * 0.6 = 0.03
    rubric_val = (1 + 2 + 0) / 9.0
    expected = min(1.0, rubric_val + 0.05 * 0.6)
    assert math.isclose(score.score, expected)
    assert score.stage == "llm"
    assert score.cached_score == score.score


@pytest.mark.asyncio
async def test_guardrail_detector_retry_and_fail_open() -> None:
    """On parse failure, retries once. If still failing, fails open with fallback or 0.0."""
    bad_res = _make_llm_result(text="invalid output", logprobs=())
    client = CountingFakeClient(responses=[bad_res, bad_res])

    fallback = StubFallbackDetector(value=0.25)
    detector = GuardrailDetector(client, mode="logprob", fallback=fallback)
    msg = _make_message("unparseable response")
    ctx = DetectorContext()

    score = await detector.ascore(msg, ctx)
    # Retried once, so 2 calls made
    assert len(client.calls) == 2
    assert detector.parse_failures == 2
    assert detector.skipped == 1
    assert score.score == 0.25
    assert score.stage == "llm"
    assert score.cached_score == 0.25


@pytest.mark.asyncio
async def test_guardrail_detector_retry_recovers() -> None:
    """If first attempt fails but retry succeeds, parse_failures is 1 and skipped is 0."""
    bad_res = _make_llm_result(text="garbled", logprobs=())
    good_lp = TokenLogprob(
        token="SAFE",
        logprob=-0.2,
        top=(("SAFE", -0.2), ("UNSAFE", -2.5)),
    )
    good_res = _make_llm_result(text="SAFE", logprobs=(good_lp,))

    client = CountingFakeClient(responses=[bad_res, good_res])
    detector = GuardrailDetector(client, mode="logprob")
    msg = _make_message("query")
    ctx = DetectorContext()

    score = await detector.ascore(msg, ctx)
    assert len(client.calls) == 2
    assert detector.parse_failures == 1
    assert detector.skipped == 0
    expected = 1.0 / (1.0 + math.exp(-0.2 - (-2.5)))
    assert math.isclose(score.score, expected)
