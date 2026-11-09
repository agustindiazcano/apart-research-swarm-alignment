"""Committed matrices preserve the declared seed and control design."""
from pathlib import Path

import yaml

from swarmlab.batch import load_matrix
from swarmlab.prereg import DEFAULT_GROUPS, collect_entries

ROOT = Path(__file__).resolve().parents[1]


def test_train_matrices_partition_seeds_and_keep_controls_clean() -> None:
    specs = [
        spec
        for path in sorted((ROOT / "experiments/configs/matrices").glob("train_*.yaml"))
        for spec in load_matrix(path)
    ]
    assert {spec.seed for spec in specs} == set(range(1, 16))
    assert len(specs) == len({spec.seed for spec in specs})
    assert {spec.arm for spec in specs} == {"TRAIN"}
    assert {spec.seed for spec in specs if not spec.extra["initial_infection"]} == set(range(1, 6))
    assert {spec.topology for spec in specs} == {"ring", "complete"}
    assert all(spec.harm == "split" and spec.defense is None for spec in specs)


def test_reported_matrices_are_paired_and_pilot_is_separate() -> None:
    directory = ROOT / "experiments/configs/matrices"
    free = load_matrix(directory / "free_flow.yaml")
    gated = load_matrix(directory / "gating.yaml")
    controls = load_matrix(directory / "control_ring.yaml") + load_matrix(
        directory / "control_complete.yaml"
    )
    seeds = set(range(101, 116))
    assert {spec.seed for spec in free} == seeds
    for topology in ("ring", "complete"):
        for harm in ("solo", "split"):
            assert {s.seed for s in free if s.topology == topology and s.harm == harm} == seeds
    for defense in ("D1", "D2", "D3", "D5"):
        assert {s.seed for s in gated if s.defense == defense} == seeds
    assert all(s.topology == "ring" and s.harm == "split" for s in gated)
    assert {s.seed for s in controls} == seeds
    assert len(controls) == len(seeds)
    assert all(not s.extra["initial_infection"] for s in controls)
    pilot = load_matrix(directory / "pilot.yaml")
    assert {s.seed for s in pilot} == set(range(901, 904))
    assert all(s.arm == "Pilot" for s in pilot)


def test_execution_configs_keep_verified_credit_units_and_shared_ledger() -> None:
    for name in ("pilot", "free_flow"):
        config = yaml.safe_load((ROOT / f"experiments/configs/{name}.yaml").read_text())
        assert config["provider"] == "adaption"
        for provider in (config, config["guardrail"]):
            assert provider["billing"]["unit"] == "credits"
            assert provider["billing"]["verified"] is True
            assert provider["billing"]["source"].startswith("https://docs.adaptionlabs.ai/")
            assert provider["billing"]["ledger_path"] == "artifacts/provider_spend.json"


def test_preregistration_hashes_every_committed_matrix() -> None:
    entries = collect_entries(ROOT, DEFAULT_GROUPS)
    hashed_configs = {entry.path for entry in entries["configs"]}
    matrices = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "experiments/configs/matrices").glob("*.yaml")
    }
    assert matrices
    assert matrices <= hashed_configs
