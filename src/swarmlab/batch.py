"""Batch runner: matrix expansion, bounded concurrency, resume, retry and balanced truncation."""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast, get_args

import yaml

from swarmlab.schema import EpisodeResult, EpisodeSpec, EpisodeStatus, Harm, Topology

logger = logging.getLogger(__name__)

EpisodeFn = Callable[[EpisodeSpec], Awaitable[EpisodeResult]]

NOT_STARTED_ERROR = "not started: budget cap reached"


def _expand_seeds(raw: Any) -> list[int]:
    if isinstance(raw, Mapping):
        if "start" not in raw or "stop" not in raw:
            raise ValueError("seeds mapping needs 'start' and 'stop'")
        start, stop = int(raw["start"]), int(raw["stop"])
        return list(range(start, stop + 1))
    return [int(s) for s in raw]


def load_matrix(source: str | Path | Mapping[str, Any]) -> list[EpisodeSpec]:
    """Expand a matrix definition into specs ordered by topology, harm, defense, seed."""
    if isinstance(source, Mapping):
        data: Mapping[str, Any] = source
    else:
        with open(source, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
        if not isinstance(loaded, Mapping):
            raise ValueError("matrix file must contain a mapping")
        data = loaded
    for key in ("arm", "topologies", "harms", "defenses", "seeds"):
        if key not in data:
            raise ValueError(f"matrix is missing key: {key}")
    arm = str(data["arm"])
    topologies = list(data["topologies"])
    harms = list(data["harms"])
    defenses = list(data["defenses"])
    seeds = _expand_seeds(data["seeds"])
    for name, values in (
        ("topologies", topologies),
        ("harms", harms),
        ("defenses", defenses),
        ("seeds", seeds),
    ):
        if not values:
            raise ValueError(f"matrix list is empty: {name}")
    for topology in topologies:
        if topology not in get_args(Topology):
            raise ValueError(f"unknown topology: {topology!r}")
    for harm in harms:
        if harm not in get_args(Harm):
            raise ValueError(f"unknown harm: {harm!r}")
    extra = dict(data.get("extra") or {})

    specs: list[EpisodeSpec] = []
    seen: set[str] = set()
    for topology, harm, defense, seed in itertools.product(topologies, harms, defenses, seeds):
        episode_id = f"{arm}-{topology}-{harm}-{defense or 'none'}-s{seed}"
        if episode_id in seen:
            raise ValueError(f"duplicate episode id: {episode_id}")
        seen.add(episode_id)
        specs.append(
            EpisodeSpec(
                episode_id=episode_id,
                seed=seed,
                topology=cast(Topology, topology),
                harm=cast(Harm, harm),
                arm=arm,
                defense=defense,
                extra=json.loads(json.dumps(extra)),
            )
        )
    return specs


def _result_path(out_dir: Path, episode_id: str) -> Path:
    return out_dir / episode_id / "result.json"


def _write_result(out_dir: Path, result: EpisodeResult, attempts: int) -> None:
    path = _result_path(out_dir, result.episode_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    payload = {**asdict(result), "attempts": attempts}
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _read_complete(out_dir: Path, episode_id: str) -> EpisodeResult | None:
    path = _result_path(out_dir, episode_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("unreadable result file, episode will run again: %s", path)
        return None
    if data.get("status") != "complete" or data.get("episode_id") != episode_id:
        return None
    return EpisodeResult(
        episode_id=episode_id,
        status="complete",
        log_path=data.get("log_path"),
        error=data.get("error"),
    )


async def run_batch(
    specs: Sequence[EpisodeSpec],
    episode_fn: EpisodeFn,
    *,
    out_dir: Path,
    max_concurrency: int = 10,
    max_retries: int = 2,
) -> list[EpisodeResult]:
    """Run all specs under one semaphore. Results follow the order of `specs`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max_concurrency)
    budget_stop = asyncio.Event()

    async def run_one(spec: EpisodeSpec) -> EpisodeResult:
        stored = _read_complete(out_dir, spec.episode_id)
        if stored is not None:
            logger.info("skip complete episode %s", spec.episode_id)
            return stored
        async with semaphore:
            if budget_stop.is_set():
                return EpisodeResult(spec.episode_id, "budget_abort", None, NOT_STARTED_ERROR)
            result: EpisodeResult | None = None
            attempts = 0
            for attempt in range(1, max_retries + 2):
                attempts = attempt
                try:
                    result = await episode_fn(spec)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("episode %s attempt %d raised: %r", spec.episode_id,
                                   attempt, exc)
                    result = EpisodeResult(
                        spec.episode_id, "failed", None, f"{type(exc).__name__}: {exc}"
                    )
                    continue
                if result.status in ("complete", "budget_abort"):
                    break
                logger.warning("episode %s attempt %d status %s", spec.episode_id, attempt,
                               result.status)
            assert result is not None
            if result.status == "budget_abort":
                budget_stop.set()
                logger.error("budget cap reached at episode %s", spec.episode_id)
            elif result.status != "complete":
                status: EpisodeStatus = "failed"
                error = result.error or f"status {result.status} after {attempts} attempts"
                result = EpisodeResult(spec.episode_id, status, result.log_path, error)
            _write_result(out_dir, result, attempts)
            logger.info("episode %s finished with status %s", spec.episode_id, result.status)
            return result

    return list(await asyncio.gather(*(run_one(s) for s in specs)))


def balanced_truncation(
    results: Sequence[EpisodeResult],
    specs: Sequence[EpisodeSpec],
    min_seeds: int = 1,
) -> list[str]:
    """Keep the k smallest completed seeds in every cell, k being the smallest cell count."""
    by_id = {s.episode_id: s for s in specs}
    completed = {r.episode_id for r in results if r.status == "complete"}
    cells: dict[tuple[str, str, str, str | None], list[EpisodeSpec]] = {}
    for spec in specs:
        key = (spec.arm, spec.topology, spec.harm, spec.defense)
        cells.setdefault(key, [])
        if spec.episode_id in completed and by_id[spec.episode_id] is spec:
            cells[key].append(spec)
    if not cells:
        return []
    k = min(len(members) for members in cells.values())
    if k < min_seeds:
        raise ValueError(f"smallest cell has {k} completed seeds, below min_seeds={min_seeds}")
    kept: list[str] = []
    for members in cells.values():
        kept.extend(s.episode_id for s in sorted(members, key=lambda s: s.seed)[:k])
    return kept
