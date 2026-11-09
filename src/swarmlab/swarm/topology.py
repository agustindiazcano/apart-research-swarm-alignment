"""Valid message targets per topology."""
from __future__ import annotations

from swarmlab.schema import Topology


def valid_targets(topology: Topology, agent_id: int, n_agents: int) -> frozenset[int]:
    """Agents that `agent_id` may address. The agent itself is never included."""
    if topology == "ring":
        return frozenset({(agent_id - 1) % n_agents, (agent_id + 1) % n_agents}) - {agent_id}
    return frozenset(range(n_agents)) - {agent_id}
