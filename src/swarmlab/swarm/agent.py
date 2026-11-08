"""Parsing of agent replies and the prompt builder interface."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from swarmlab.schema import ActionPayload
from swarmlab.world.types import AgentSeed


class PromptBuilder(Protocol):
    def build(
        self,
        seed: AgentSeed,
        inbox: Sequence[tuple[int, int, str]],
        notices: Sequence[str],
        round_index: int,
        rounds: int,
        n_agents: int,
    ) -> list[dict[str, str]]: ...


def _first_object(raw: str) -> object:
    """Decode the first JSON object found in `raw`. Raises ValueError when none decodes."""
    decoder = json.JSONDecoder()
    start = raw.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            start = raw.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = raw.find("{", start + 1)
    raise ValueError("no JSON object found")


def parse_action(raw: str) -> tuple[ActionPayload | None, str | None]:
    """Extract the first JSON object in `raw` and build an ActionPayload."""
    try:
        data = _first_object(raw)
        if not isinstance(data, dict):
            return None, "no JSON object found"
        return ActionPayload.from_dict(data), None
    except (ValueError, TypeError, AttributeError) as exc:
        return None, str(exc)
