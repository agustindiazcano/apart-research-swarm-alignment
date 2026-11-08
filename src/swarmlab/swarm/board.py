"""Message store: pending messages, delivered inboxes and per-agent notices."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Delivered:
    """A direct message. `round` is the round in which it was sent."""

    message_id: str
    round: int
    sender: int
    target: int
    text: str
    cached_score: float | None = None


class Board:
    """Messages added during a round become visible when `commit_round` is called."""

    def __init__(self, n_agents: int, k_inbox: int = 10) -> None:
        self.n_agents = n_agents
        self.k_inbox = k_inbox
        self._pending: list[Delivered] = []
        self._history: list[list[Delivered]] = [[] for _ in range(n_agents)]
        self._notices: list[list[str]] = [[] for _ in range(n_agents)]

    def add_pending(self, msg: Delivered) -> None:
        self._pending.append(msg)

    def commit_round(self, round_index: int) -> None:
        """Move pending messages to the inbox of their target. `round_index` is unused
        for ordering: messages keep the round in which they were sent."""
        del round_index
        for msg in self._pending:
            self._history[msg.target].append(msg)
        self._pending = []

    def inbox(self, agent_id: int) -> list[Delivered]:
        """Last K delivered messages addressed to the agent, oldest first."""
        return list(self._history[agent_id][-self.k_inbox :])

    def received_in_round(self, agent_id: int, round_index: int) -> list[Delivered]:
        """Messages addressed to the agent that were sent in `round_index` and delivered."""
        return [m for m in self._history[agent_id] if m.round == round_index]

    def add_notice(self, agent_id: int, text: str) -> None:
        self._notices[agent_id].append(text)

    def pop_notices(self, agent_id: int) -> list[str]:
        notices = self._notices[agent_id]
        self._notices[agent_id] = []
        return notices
