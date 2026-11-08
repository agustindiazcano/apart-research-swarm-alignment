"""Vertex Gemini adapter using ADC, intended to be wrapped by GuardedClient."""
from __future__ import annotations

import importlib
import time
from collections.abc import Iterable, Mapping, Sequence
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


class VertexClient:
    """Translate text roles to Gemini contents and keep reasoning usage in output cost."""

    def __init__(
        self, model: str, *, project: str | None = None, location: str | None = None,
        client: Any = None, secrets: Iterable[str] = (),
    ) -> None:
        self.model = model
        self._secrets = tuple(secrets)
        self._owns_client = client is None
        if client is None:
            if not project or not location:
                raise ValueError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are required")
            try:
                sdk = importlib.import_module("google.genai")
            except ImportError:
                raise ImportError("Install the google-genai package to use VertexClient") from None
            try:
                client = sdk.Client(
                    vertexai=True, project=project, location=location,
                    http_options={"retry_options": {"attempts": 1}},
                )
            except Exception as exc:
                raise translated_error("vertex", exc, self._secrets) from None
        self._client = client

    @classmethod
    def from_env(
        cls, model: str, *, environ: Mapping[str, str] | None = None, client: Any = None,
        secrets: Iterable[str] = (),
    ) -> VertexClient:
        return cls(
            model, project=required_env("GOOGLE_CLOUD_PROJECT", environ),
            location=required_env("GOOGLE_CLOUD_LOCATION", environ), client=client, secrets=secrets,
        )

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, temperature: float | None = None,
        max_tokens: int = 256, logprobs: bool = False,
    ) -> LLMResult:
        validated = validate_request(messages, temperature, max_tokens, logprobs)
        system: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in validated:
            if message["role"] == "system":
                if contents:
                    raise ValueError("Vertex system messages must precede conversation messages")
                system.append(message["content"])
            else:
                contents.append({
                    "role": "model" if message["role"] == "assistant" else "user",
                    "parts": [{"text": message["content"]}],
                })
        if not contents:
            raise ValueError("Vertex requires a conversation message")
        config: dict[str, Any] = {"max_output_tokens": max_tokens}
        if system:
            config["system_instruction"] = "\n".join(system)
        if temperature is not None:
            config["temperature"] = temperature
        started = time.perf_counter()
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model, contents=contents, config=config,
            )
            usage = field(response, "usage_metadata")
            output_tokens = token_count(usage, "candidates_token_count")
            thoughts = field(usage, "thoughts_token_count")
            if thoughts is not None:
                output_tokens += token_count(usage, "thoughts_token_count")
            candidates = field(response, "candidates") or []
            finish = field(candidates[0], "finish_reason") if candidates else None
            if finish is None:
                finish = field(field(response, "prompt_feedback"), "block_reason")
            finish = field(finish, "value", finish)
            return LLMResult(
                text=field(response, "text") or "", provider="vertex", model=self.model,
                response_id=field(response, "response_id"),
                tokens_in=token_count(usage, "prompt_token_count"), tokens_out=output_tokens,
                latency_ms=(time.perf_counter() - started) * 1000,
                finish_reason=finish, timestamp_utc=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            raise translated_error("vertex", exc, self._secrets) from None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aio.aclose()
