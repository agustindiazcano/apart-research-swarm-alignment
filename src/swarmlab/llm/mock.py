"""Scripted mock LLM client for testing and offline evaluation."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from swarmlab.schema import LLMResult, TokenLogprob

logger = logging.getLogger(__name__)


def _extract_prompt_text(messages: Sequence[Mapping[str, str]]) -> str:
    """Concatenate message texts to compute prompt length."""
    parts: list[str] = []
    for m in messages:
        if "content" in m:
            parts.append(str(m["content"]))
        elif "text" in m:
            parts.append(str(m["text"]))
        else:
            parts.extend(str(v) for v in m.values())
    return "".join(parts)


class MockClient:
    """Scripted mock client implementing the LLMClient protocol."""

    def __init__(
        self,
        responder: Callable[[Sequence[Mapping[str, str]]], str] | Sequence[str],
        *,
        provider: str = "mock",
        model: str = "mock-1",
        logprob_pair: tuple[str, str, float] | None = None,
    ) -> None:
        self._responder = responder
        self._provider = provider
        self._model = model
        self._logprob_pair = logprob_pair
        self._seq_index: int = 0
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        """Return scripted reply and record call arguments."""
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "logprobs": logprobs,
            }
        )
        call_number = len(self.calls)

        if callable(self._responder):
            reply_text = self._responder(messages)
        else:
            if self._seq_index >= len(self._responder):
                raise IndexError(
                    f"Mock responder exhausted: requested call {call_number} "
                    f"with only {len(self._responder)} replies"
                )
            reply_text = self._responder[self._seq_index]
            self._seq_index += 1

        prompt_str = _extract_prompt_text(messages)
        tokens_in = max(1, len(prompt_str) // 4)
        tokens_out = max(1, len(reply_text) // 4)

        logprobs_tuple: tuple[TokenLogprob, ...] | None = None
        if logprobs and self._logprob_pair is not None:
            token_a, token_b, p_a = self._logprob_pair
            lp_a = math.log(p_a)
            lp_b = math.log(1.0 - p_a)
            logprobs_tuple = (
                TokenLogprob(
                    token=token_a,
                    logprob=lp_a,
                    top=((token_a, lp_a), (token_b, lp_b)),
                ),
            )

        now_utc = datetime.now(UTC).isoformat()
        return LLMResult(
            text=reply_text,
            provider=self._provider,
            model=self._model,
            response_id=f"mock-{call_number}",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=0.0,
            finish_reason="stop",
            logprobs=logprobs_tuple,
            timestamp_utc=now_utc,
        )
