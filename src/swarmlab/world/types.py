"""Types produced by the world generator and consumed by the swarm core."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from swarmlab.schema import GroundTruth

Role = Literal["standard", "patient_zero"]


@dataclass(frozen=True)
class AgentSeed:
    """Everything an agent may know at the start of an episode."""

    agent_id: int
    role: Role
    records: tuple[str, ...]  # three private work records (the benign job)
    audit_tag: str  # NODE_AUDIT_TAG value: a fragment, the full code, or "none"
    playbook_style: int | None  # 0, 1 or 2 for the patient zero, None for everyone else
    neighbors: tuple[int, int]  # ring neighbors (i - 1, i + 1) modulo n_agents
    verifier: bool  # carries the verification protocol (immunity arm)


@dataclass(frozen=True)
class World:
    """One generated episode world: ground truth (never shown to agents) and agent seeds."""

    ground_truth: GroundTruth
    agents: tuple[AgentSeed, ...]
