"""D5 layered filter, single-detector threshold gates, and gate decision types."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from swarmlab.detectors.graph import graph_score
from swarmlab.schema import (
    Detector,
    DetectorContext,
    DetectorScore,
    MessageView,
)


@dataclass(frozen=True)
class GateDecision:
    """Outcome of evaluating a message against a gate."""

    blocked: bool
    score: float
    stage: Literal["d1", "llm", "graph"]
    cached_score: float


@runtime_checkable
class AsyncDetector(Protocol):
    """Protocol for detectors exposing an asynchronous ascore method."""

    name: str

    async def ascore(
        self,
        message: MessageView,
        context: DetectorContext,
    ) -> DetectorScore: ...


class ThresholdGate:
    """Single-detector gate applying a threshold to D1, D2, or D3 alone."""

    def __init__(self, detector: Detector | AsyncDetector, threshold: float) -> None:
        self.detector = detector
        self.threshold = threshold

    async def decide(
        self,
        message: MessageView,
        context: DetectorContext,
    ) -> GateDecision:
        """Evaluate message against threshold and return a GateDecision."""
        if isinstance(self.detector, AsyncDetector):
            res = await self.detector.ascore(message, context)
            score = res.score
            cached = res.cached_score if res.cached_score is not None else score
            if res.stage in ("d1", "llm", "graph"):
                stage = res.stage
            elif getattr(self.detector, "name", "") == "d2":
                stage = "llm"
            elif getattr(self.detector, "name", "") == "d3":
                stage = "graph"
            else:
                stage = "d1"
        else:
            score = self.detector.score(message, context)
            cached = score
            det_name = getattr(self.detector, "name", "")
            if det_name == "d3":
                stage = "graph"
            elif det_name == "d2":
                stage = "llm"
            else:
                stage = "d1"

        blocked = bool(score >= self.threshold)
        return GateDecision(
            blocked=blocked,
            score=score,
            stage=stage,
            cached_score=cached,
        )


class LayeredFilter:
    """D5 layered filter routing messages through fast stage 1 and graph-contextual stage 2."""

    def __init__(
        self,
        d1: Detector,
        d2: AsyncDetector,
        *,
        t_low: float,
        t_high: float,
        tau_stage2: float,
        lam: float,
        tau_floor: float,
    ) -> None:
        self.d1 = d1
        self.d2 = d2
        self.t_low = t_low
        self.t_high = t_high
        self.tau_stage2 = tau_stage2
        self.lam = lam
        self.tau_floor = tau_floor
        self.llm_calls: int = 0
        self.decisions: int = 0

    async def decide(
        self,
        message: MessageView,
        context: DetectorContext,
    ) -> GateDecision:
        """Score message with D1; fast pass/block outside gray zone, else route to D2 + graph."""
        self.decisions += 1
        s1 = self.d1.score(message, context)

        if s1 < self.t_low:
            return GateDecision(
                blocked=False,
                score=s1,
                stage="d1",
                cached_score=s1,
            )

        if s1 > self.t_high:
            return GateDecision(
                blocked=True,
                score=s1,
                stage="d1",
                cached_score=s1,
            )

        self.llm_calls += 1
        d2_res = await self.d2.ascore(message, context)
        s2 = d2_res.score
        s_graph = graph_score(
            s2,
            context.inbox_cached_scores,
            lam=self.lam,
            tau_floor=self.tau_floor,
        )
        blocked = bool(s_graph >= self.tau_stage2)
        cached = d2_res.cached_score if d2_res.cached_score is not None else s2

        return GateDecision(
            blocked=blocked,
            score=s_graph,
            stage="graph",
            cached_score=cached,
        )


def cached_score_for_context(
    decisions: Sequence[GateDecision],
) -> tuple[float, ...]:
    """Return the cached_score values from a sequence of gate decisions."""
    return tuple(d.cached_score for d in decisions)
