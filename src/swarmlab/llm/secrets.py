"""Secret retrieval and string redaction utilities."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping

logger = logging.getLogger(__name__)


def read_secret(name: str, environ: Mapping[str, str] | None = None) -> str:
    """Read a secret from the environment, raising KeyError without exposing any values."""
    env = os.environ if environ is None else environ
    if name not in env or env[name] is None:
        raise KeyError(f"Secret variable '{name}' not found")
    return env[name]


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace occurrences of each non-empty secret with [REDACTED]."""
    unique_secrets = sorted({s for s in secrets if s}, key=len, reverse=True)
    for secret in unique_secrets:
        text = text.replace(secret, "[REDACTED]")
    return text
