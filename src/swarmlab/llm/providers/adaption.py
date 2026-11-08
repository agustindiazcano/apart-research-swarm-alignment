"""Adaption Responses adapter, intended to be wrapped by GuardedClient."""
from __future__ import annotations

import importlib
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from swarmlab.llm.providers._common import (
    field,
    required_env,
    token_count,
    translated_error,
    validate_request,
)
from swarmlab.schema import LLMResult


class AdaptionClient:
    """Use the async SDK, with retry policy owned by GuardedClient."""

    def __init__(self, model: str, *, api_key: str, client: Any = None) -> None:
        if not api_key.strip():
            raise ValueError("ADAPTION_API_KEY must not be empty")
        self.model = model
        self._api_key = api_key
        self._owns_client = client is None
        if client is None:
            try:
                sdk = importlib.import_module("adaption")
            except ImportError:
                raise ImportError("Install the adaption package to use AdaptionClient") from None
            try:
                client = sdk.AsyncAdaption(api_key=api_key, max_retries=0)
            except Exception as exc:
                raise translated_error("adaption", exc, [api_key]) from None
        self._client = client

    @classmethod
    def from_env(
        cls, model: str, *, environ: Mapping[str, str] | None = None, client: Any = None,
    ) -> AdaptionClient:
        return cls(model, api_key=required_env("ADAPTION_API_KEY", environ), client=client)

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, temperature: float | None = None,
        max_tokens: int = 256, logprobs: bool = False,
    ) -> LLMResult:
        validated = validate_request(messages, temperature, max_tokens, logprobs)
        kwargs: dict[str, Any] = {
            "model": self.model, "input": validated,
            "max_output_tokens": max_tokens, "store": False,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        started = time.perf_counter()
        try:
            response = await self._client.responses.create(**kwargs)
            if field(response, "error") is not None or field(response, "status") == "failed":
                raise RuntimeError("Provider returned a failed response")
            usage = field(response, "usage")
            text = field(response, "output_text")
            if not isinstance(text, str):
                raise RuntimeError("Provider returned no text field")
            finish = field(field(response, "incomplete_details"), "reason")
            return LLMResult(
                text=text, provider="adaption", model=self.model,
                response_id=field(response, "id"), tokens_in=token_count(usage, "input_tokens"),
                tokens_out=token_count(usage, "output_tokens"),
                latency_ms=(time.perf_counter() - started) * 1000,
                finish_reason=finish or field(response, "status"),
                timestamp_utc=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            raise translated_error("adaption", exc, [self._api_key]) from None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()
