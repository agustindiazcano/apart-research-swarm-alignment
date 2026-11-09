"""Async D3 adapter using the supplied previous-round inbox and one D2 invocation."""

from __future__ import annotations

from swarmlab.detectors.graph import graph_score
from swarmlab.detectors.layered import AsyncDetector
from swarmlab.schema import DetectorContext, DetectorScore, MessageView


class GraphDetector:
    name = "d3"

    def __init__(self, d2: AsyncDetector, *, lam: float, tau_floor: float) -> None:
        self.d2, self.lam, self.tau_floor = d2, lam, tau_floor

    async def ascore(self, message: MessageView, context: DetectorContext) -> DetectorScore:
        local = await self.d2.ascore(message, context)
        score = graph_score(
            local.score, context.inbox_cached_scores, lam=self.lam, tau_floor=self.tau_floor
        )
        return DetectorScore(message.message_id, self.name, score, "graph", local.score)
