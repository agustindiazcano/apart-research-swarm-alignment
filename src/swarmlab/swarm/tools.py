"""Validation of agent actions. Application of actions is done by the runner."""
from __future__ import annotations

from swarmlab.schema import ActionPayload, Topology
from swarmlab.swarm.topology import valid_targets


def validate_action(
    action: ActionPayload, sender: int, topology: Topology, n_agents: int
) -> str | None:
    """Return a rejection reason, or None when the action is allowed."""
    if action.action != "post":
        return None
    if action.to is None:
        return "post without target"
    if action.intent is None:
        return "post without intent"
    if action.to not in valid_targets(topology, sender, n_agents):
        return "target not allowed in topology"
    return None
