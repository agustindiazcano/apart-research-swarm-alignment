"""Tests for the batch runner: matrix expansion, concurrency, resume, retry, budget, truncation."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swarmlab.batch import balanced_truncation, load_matrix, run_batch  # noqa: E402
from swarmlab.schema import EpisodeResult, EpisodeSpec  # noqa: E402


def _matrix(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "arm": "A1",
        "topologies": ["ring", "complete"],
        "harms": ["solo", "split"],
        "defenses": [None, "D1"],
        "seeds": [1, 2],
    }
    base.update(overrides)
    return base


def _specs(n: int) -> list[EpisodeSpec]:
    return load_matrix(
        _matrix(
            topologies=["ring"],
            harms=["solo"],
            defenses=[None],
            seeds={"start": 1, "stop": n},
        )
    )


def _ok(spec: EpisodeSpec) -> EpisodeResult:
    return EpisodeResult(spec.episode_id, "complete", f"{spec.episode_id}/events.jsonl", None)


def test_matrix_order_and_ids() -> None:
    specs = load_matrix(_matrix())
    assert len(specs) == 2 * 2 * 2 * 2
    assert specs[0].episode_id == "A1-ring-solo-none-s1"
    assert specs[1].episode_id == "A1-ring-solo-none-s2"
    assert specs[2].episode_id == "A1-ring-solo-D1-s1"
    assert specs[4].episode_id == "A1-ring-split-none-s1"
    assert specs[8].episode_id == "A1-complete-solo-none-s1"
    assert specs[0].defense is None
    assert specs[2].defense == "D1"
    assert specs[0].seed == 1 and specs[0].arm == "A1"


def test_seeds_range_mapping_is_inclusive() -> None:
    specs = load_matrix(
        _matrix(seeds={"start": 3, "stop": 6}, topologies=["ring"], harms=["solo"],
                defenses=[None])
    )
    assert [s.seed for s in specs] == [3, 4, 5, 6]


def test_extra_copied_into_every_spec() -> None:
    specs = load_matrix(_matrix(extra={"rounds": 5}))
    assert all(s.extra == {"rounds": 5} for s in specs)
    specs[0].extra["rounds"] = 9
    assert specs[1].extra == {"rounds": 5}


def test_empty_list_rejected() -> None:
    for key in ("topologies", "harms", "defenses", "seeds"):
        with pytest.raises(ValueError):
            load_matrix(_matrix(**{key: []}))


def test_duplicate_ids_rejected() -> None:
    with pytest.raises(ValueError):
        load_matrix(_matrix(seeds=[1, 1]))


def test_load_from_yaml_file(tmp_path: Path) -> None:
    path = tmp_path / "matrix.yaml"
    path.write_text(
        "arm: A0\ntopologies: [ring]\nharms: [solo]\ndefenses: [null, D2]\n"
        "seeds: {start: 1, stop: 2}\nextra: {rounds: 4}\n",
        encoding="utf-8",
    )
    for source in (path, str(path)):
        specs = load_matrix(source)
        assert [s.episode_id for s in specs] == [
            "A0-ring-solo-none-s1",
            "A0-ring-solo-none-s2",
            "A0-ring-solo-D2-s1",
            "A0-ring-solo-D2-s2",
        ]
        assert specs[0].extra == {"rounds": 4}


def test_concurrency_limit(tmp_path: Path) -> None:
    specs = _specs(10)
    state = {"now": 0, "max": 0}

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return _ok(spec)

    results = asyncio.run(run_batch(specs, fn, out_dir=tmp_path, max_concurrency=3))
    assert state["max"] == 3
    assert [r.episode_id for r in results] == [s.episode_id for s in specs]
    assert all(r.status == "complete" for r in results)


def test_result_json_stored_with_attempts(tmp_path: Path) -> None:
    specs = _specs(1)

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        return _ok(spec)

    asyncio.run(run_batch(specs, fn, out_dir=tmp_path))
    data = json.loads((tmp_path / specs[0].episode_id / "result.json").read_text("utf-8"))
    assert data["status"] == "complete"
    assert data["episode_id"] == specs[0].episode_id
    assert data["attempts"] == 1


def test_resume_skips_complete(tmp_path: Path) -> None:
    specs = _specs(6)
    calls: dict[str, int] = {}

    async def first(spec: EpisodeSpec) -> EpisodeResult:
        calls[spec.episode_id] = calls.get(spec.episode_id, 0) + 1
        if spec.seed <= 3:
            return _ok(spec)
        return EpisodeResult(spec.episode_id, "failed", None, "boom")

    asyncio.run(run_batch(specs, first, out_dir=tmp_path, max_retries=0))
    calls.clear()

    async def second(spec: EpisodeSpec) -> EpisodeResult:
        calls[spec.episode_id] = calls.get(spec.episode_id, 0) + 1
        return _ok(spec)

    results = asyncio.run(run_batch(specs, second, out_dir=tmp_path))
    assert set(calls) == {s.episode_id for s in specs if s.seed > 3}
    assert all(v == 1 for v in calls.values())
    assert all(r.status == "complete" for r in results)
    assert results[0].log_path == f"{specs[0].episode_id}/events.jsonl"


def test_retry_then_success(tmp_path: Path) -> None:
    specs = _specs(1)
    seeds: list[int] = []

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        seeds.append(spec.seed)
        if len(seeds) <= 2:
            return EpisodeResult(spec.episode_id, "infra_failure", None, "timeout")
        return _ok(spec)

    results = asyncio.run(run_batch(specs, fn, out_dir=tmp_path, max_retries=2))
    assert seeds == [1, 1, 1]
    assert results[0].status == "complete"
    data = json.loads((tmp_path / specs[0].episode_id / "result.json").read_text("utf-8"))
    assert data["attempts"] == 3


def test_always_failing_is_reported(tmp_path: Path) -> None:
    specs = _specs(2)
    count = {"n": 0}

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        count["n"] += 1
        return EpisodeResult(spec.episode_id, "failed", None, "bad output")

    results = asyncio.run(run_batch(specs, fn, out_dir=tmp_path, max_retries=2))
    assert count["n"] == 2 * 3
    assert len(results) == 2
    assert all(r.status == "failed" and r.error for r in results)
    assert (tmp_path / specs[0].episode_id / "result.json").exists()


def test_exception_treated_as_failure(tmp_path: Path) -> None:
    specs = _specs(1)
    count = {"n": 0}

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        count["n"] += 1
        if count["n"] < 2:
            raise RuntimeError("provider down")
        return _ok(spec)

    results = asyncio.run(run_batch(specs, fn, out_dir=tmp_path, max_retries=2))
    assert count["n"] == 2
    assert results[0].status == "complete"

    async def always_raises(spec: EpisodeSpec) -> EpisodeResult:
        raise RuntimeError("provider down")

    other = tmp_path / "other"
    results = asyncio.run(run_batch(specs, always_raises, out_dir=other, max_retries=1))
    assert results[0].status == "failed"
    assert results[0].error is not None and "provider down" in results[0].error


def test_budget_abort_stops_new_episodes(tmp_path: Path) -> None:
    specs = _specs(6)
    called: list[str] = []

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        called.append(spec.episode_id)
        if spec.seed == 2:
            return EpisodeResult(spec.episode_id, "budget_abort", None, "cap")
        return _ok(spec)

    results = asyncio.run(run_batch(specs, fn, out_dir=tmp_path, max_concurrency=1))
    assert called == [specs[0].episode_id, specs[1].episode_id]
    assert [r.status for r in results] == ["complete"] + ["budget_abort"] * 5
    assert results[1].error == "cap"
    for r in results[2:]:
        assert r.error == "not started: budget cap reached"
        assert not (tmp_path / r.episode_id / "result.json").exists()
    stored = json.loads((tmp_path / specs[1].episode_id / "result.json").read_text("utf-8"))
    assert stored["status"] == "budget_abort"


def test_no_temp_files_remain(tmp_path: Path) -> None:
    specs = _specs(4)

    async def fn(spec: EpisodeSpec) -> EpisodeResult:
        return _ok(spec)

    asyncio.run(run_batch(specs, fn, out_dir=tmp_path))
    names = sorted(p.name for p in tmp_path.rglob("*") if p.is_file())
    assert names == ["result.json"] * 4


def _results(specs: list[EpisodeSpec], failed: set[str]) -> list[EpisodeResult]:
    return [
        EpisodeResult(s.episode_id, "failed" if s.episode_id in failed else "complete", None, None)
        for s in specs
    ]


def test_balanced_truncation_equalizes_cells() -> None:
    specs = load_matrix(
        _matrix(topologies=["ring"], harms=["solo"], defenses=[None, "D1"], seeds=[1, 2, 3, 4])
    )
    failed = {"A1-ring-solo-D1-s1", "A1-ring-solo-D1-s3"}
    kept = balanced_truncation(_results(specs, failed), specs)
    assert kept == [
        "A1-ring-solo-none-s1",
        "A1-ring-solo-none-s2",
        "A1-ring-solo-D1-s2",
        "A1-ring-solo-D1-s4",
    ]


def test_balanced_truncation_min_seeds_violation() -> None:
    specs = load_matrix(
        _matrix(topologies=["ring"], harms=["solo"], defenses=[None, "D1"], seeds=[1, 2, 3])
    )
    failed = {"A1-ring-solo-D1-s1", "A1-ring-solo-D1-s2"}
    with pytest.raises(ValueError):
        balanced_truncation(_results(specs, failed), specs, min_seeds=2)


def test_balanced_truncation_empty_cell_gives_zero() -> None:
    specs = load_matrix(
        _matrix(topologies=["ring"], harms=["solo"], defenses=[None, "D1"], seeds=[1, 2])
    )
    failed = {"A1-ring-solo-D1-s1", "A1-ring-solo-D1-s2"}
    with pytest.raises(ValueError):
        balanced_truncation(_results(specs, failed), specs, min_seeds=1)
    assert balanced_truncation(_results(specs, failed), specs, min_seeds=0) == []
