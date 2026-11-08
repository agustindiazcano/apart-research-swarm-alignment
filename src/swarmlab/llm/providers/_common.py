"""Validation and sanitized error translation shared by provider adapters."""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import httpx

from swarmlab.llm.limiter import RetryableError
from swarmlab.llm.secrets import read_secret, redact


def required_env(name: str, environ: Mapping[str, str] | None = None) -> str:
    value = read_secret(name, environ)
    if not value.strip():
        raise ValueError(f"Environment variable {name} must not be empty")
    return value


def validate_request(
    messages: Sequence[Mapping[str, str]],
    temperature: float | None,
    max_tokens: int,
    logprobs: bool,
) -> list[dict[str, str]]:
    if logprobs:
        raise ValueError("logprobs are not supported by the configured provider adapters")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
        raise ValueError("max_tokens must be a positive integer")
    if temperature is not None and (not math.isfinite(temperature) or temperature < 0):
        raise ValueError("temperature must be finite and nonnegative")
    result = []
    for message in messages:
        if message.get("role") not in {"system", "user", "assistant"}:
            raise ValueError("Unsupported message role")
        if not isinstance(message.get("content"), str):
            raise ValueError("Message content must be text")
        result.append({"role": message["role"], "content": message["content"]})
    if not result:
        raise ValueError("messages must not be empty")
    return result


def field(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def token_count(usage: Any, name: str) -> int:
    value = field(usage, name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RuntimeError(f"Missing or invalid token usage field {name}")
    return value


def translated_error(provider: str, error: Exception, secrets: Iterable[str]) -> Exception:
    """Remove configured secrets and suppress raw provider exception chaining at call sites."""
    status = field(error, "status_code", field(error, "code"))
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
    message = redact(f"{provider} request failed (status={status}): {error}", secrets)
    if (
        isinstance(error, (TimeoutError, httpx.TimeoutException))
        or "Timeout" in type(error).__name__
    ):
        return TimeoutError(message)
    if (
        status == 429
        or isinstance(status, int) and 500 <= status < 600
        or isinstance(error, httpx.TransportError)
        or "ConnectionError" in type(error).__name__
    ):
        return RetryableError(message)
    return RuntimeError(message)
