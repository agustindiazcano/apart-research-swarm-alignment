"""Meta Muse chat-completions adapter, intended to be wrapped by GuardedClient."""
from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import httpx

from swarmlab.llm.providers._common import (
    required_env,
    token_count,
    translated_error,
    validate_request,
)
from swarmlab.schema import LLMResult


class MuseClient:
    """Translate the frozen LLMClient contract to Muse requests without internal retries."""

    def __init__(
        self, model: str, *, api_key: str, http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("META_MUSE_API_KEY must not be empty")
        self.model = model
        self._api_key = api_key
        self._http_client = http_client

    @classmethod
    def from_env(
        cls, model: str, *, environ: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> MuseClient:
        return cls(
            model, api_key=required_env("META_MUSE_API_KEY", environ), http_client=http_client,
        )

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, temperature: float | None = None,
        max_tokens: int = 256, logprobs: bool = False,
    ) -> LLMResult:
        validated = validate_request(messages, temperature, max_tokens, logprobs)
        body: dict[str, object] = {
            "model": self.model, "messages": validated, "max_completion_tokens": max_tokens,
        }
        if temperature is not None:
            body["temperature"] = temperature
        started = time.perf_counter()
        try:
            if self._http_client is None:
                async with httpx.AsyncClient() as http:
                    response = await self._post(http, body)
            else:
                response = await self._post(self._http_client, body)
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
            if not isinstance(text, str):
                raise RuntimeError("Provider returned non-text content")
            usage = data.get("usage")
            return LLMResult(
                text=text, provider="muse", model=data.get("model", self.model),
                response_id=data.get("id"), tokens_in=token_count(usage, "prompt_tokens"),
                tokens_out=token_count(usage, "completion_tokens"),
                latency_ms=(time.perf_counter() - started) * 1000,
                finish_reason=choice.get("finish_reason"),
                timestamp_utc=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            raise translated_error("muse", exc, [self._api_key]) from None

    async def _post(self, http: httpx.AsyncClient, body: dict[str, object]) -> httpx.Response:
        response = await http.post(
            "https://api.meta.ai/v1/chat/completions", json=body,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        response.raise_for_status()
        return response
