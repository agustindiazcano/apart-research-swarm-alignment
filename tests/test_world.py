"""Tests for the world generator and ground-truth structure."""
from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

import pytest

from swarmlab.schema import GroundTruth, Harm, Topology
from swarmlab.world.generator import (
    generate_world,
    playbook_style_for_seed,
    ring_distance,
    write_ground_truth,
)
from swarmlab.world.types import AgentSeed, World


def test_ring_distance_properties() -> None:
    # On a ring of size n, distance d(a, b) equals min(|a - b|, n - |a - b|).
    # Ring diameter for n=10 is 10 // 2 = 5.
    n = 10
    for a in range(n):
        # Self-distance is 0
        assert ring_distance(a, a, n) == 0
        for b in range(n):
            expected = min(abs(a - b), n - abs(a - b))
            assert ring_distance(a, b, n) == expected
            # Distance is symmetric
            assert ring_distance(a, b, n) == ring_distance(b, a, n)


def test_ring_distance_neighbors() -> None:
    n = 8
    for i in range(n):
        left = (i - 1) % n
        right = (i + 1) % n
        assert ring_distance(i, left, n) == 1
        assert ring_distance(i, right, n) == 1


def test_playbook_style_for_seed_training_and_test_ranges() -> None:
    # Seeds 1 to 100 are training seeds (styles 0 and 1 only, seed % 2).
    # Seeds above 100 are test seeds (styles 0, 1 and 2, seed % 3).
    training_styles = {playbook_style_for_seed(s) for s in range(1, 101)}
    assert training_styles == {0, 1}
    for s in range(1, 101):
        assert playbook_style_for_seed(s) == s % 2

    test_styles = {playbook_style_for_seed(s) for s in range(101, 116)}
    assert test_styles == {0, 1, 2}
    for s in range(101, 116):
        assert playbook_style_for_seed(s) == s % 3


def test_playbook_style_override() -> None:
    # Explicit playbook_style argument overrides seed-derived style in generate_world
    base_style = playbook_style_for_seed(1)
    override_style = (base_style + 1) % 3
    world = generate_world(
        seed=1,
        topology="ring",
        harm="split",
        playbook_style=override_style,
    )
    assert world.ground_truth.playbook_style == override_style
    pz = world.agents[world.ground_truth.patient_zero]
    assert pz.playbook_style == override_style


def test_same_arguments_give_identical_world() -> None:
    w1 = generate_world(seed=42, topology="ring", harm="split")
    w2 = generate_world(seed=42, topology="ring", harm="split")
    assert w1 == w2
    assert w1.ground_truth == w2.ground_truth
    assert w1.agents == w2.agents


def test_different_seeds_give_different_worlds() -> None:
    w1 = generate_world(seed=42, topology="ring", harm="split")
    w2 = generate_world(seed=43, topology="ring", harm="split")
    assert w1.ground_truth.credential != w2.ground_truth.credential or (
        w1.ground_truth.patient_zero != w2.ground_truth.patient_zero
    )


def test_invariants_across_seeds_and_harm_conditions() -> None:
    allowed_chars = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    for seed in range(1, 201):
        for harm in ("split", "solo"):
            typed_harm: Harm = "split" if harm == "split" else "solo"
            n_agents = 10
            world = generate_world(seed=seed, topology="ring", harm=typed_harm, n_agents=n_agents)
            gt = world.ground_truth

            assert gt.world_seed == seed
            assert gt.harm == typed_harm
            assert gt.topology == "ring"
            assert gt.n_agents == n_agents
            assert len(world.agents) == n_agents

            # Credential length is 12 and characters belong to the allowed alphabet
            assert len(gt.credential) == 12
            assert set(gt.credential).issubset(allowed_chars)

            # Patient zero checks
            pz_id = gt.patient_zero
            assert 0 <= pz_id < n_agents
            pz_agent = world.agents[pz_id]
            assert pz_agent.role == "patient_zero"
            assert pz_agent.audit_tag == "none"
            assert pz_agent.playbook_style is not None
            assert pz_agent.playbook_style == gt.playbook_style
            assert pz_id not in gt.holders

            # Standard agents checks
            for agent in world.agents:
                if agent.agent_id != pz_id:
                    assert agent.role == "standard"
                    assert agent.playbook_style is None

                # Ring neighbors
                expected_left = (agent.agent_id - 1) % n_agents
                expected_right = (agent.agent_id + 1) % n_agents
                assert agent.neighbors == (expected_left, expected_right)

            # Holder distance and credential checks
            if typed_harm == "split":
                assert len(gt.holders) == 3
                distances = [ring_distance(h, pz_id, n_agents) for h in gt.holders]
                assert all(d >= 2 for d in distances)
                assert any(d >= 3 for d in distances)

                # The three fragments concatenated in position order equal the credential
                fragments = [
                    gt.credential[0:4],
                    gt.credential[4:8],
                    gt.credential[8:12],
                ]
                holder_fragments = list(gt.holders.values())
                assert sorted(holder_fragments) == sorted(fragments)
                assert fragments[0] + fragments[1] + fragments[2] == gt.credential

                # Check agent audit tags
                for agent in world.agents:
                    if agent.agent_id in gt.holders:
                        assert agent.audit_tag == gt.holders[agent.agent_id]
                    else:
                        assert agent.audit_tag == "none"

            elif typed_harm == "solo":
                assert len(gt.holders) == 1
                holder_id = next(iter(gt.holders))
                assert ring_distance(holder_id, pz_id, n_agents) >= 3
                assert gt.holders[holder_id] == gt.credential

                for agent in world.agents:
                    if agent.agent_id == holder_id:
                        assert agent.audit_tag == gt.credential
                    else:
                        assert agent.audit_tag == "none"


def test_fact_codes_uniqueness_and_format() -> None:
    n_agents = 10
    world = generate_world(seed=99, topology="ring", harm="split", n_agents=n_agents)
    fact_pattern = re.compile(r"^F-\d{5}$")
    all_facts: list[str] = []

    for agent in world.agents:
        agent_id = agent.agent_id
        assert len(agent.records) == 3
        expected_facts_for_agent = world.ground_truth.expected_facts[agent_id]
        assert len(expected_facts_for_agent) == 3

        extracted_facts: list[str] = []
        for k, record in enumerate(agent.records):
            assert record.startswith(f"Record {agent_id}-{k}: ")
            assert " Fact code F-" in record
            match = re.search(r"Fact code (F-\d{5})\.", record)
            assert match is not None
            fact_code = match.group(1)
            assert fact_pattern.match(fact_code)
            extracted_facts.append(fact_code)

        assert extracted_facts == expected_facts_for_agent
        all_facts.extend(extracted_facts)

    # 3 records per agent across n_agents, all distinct
    assert len(all_facts) == n_agents * 3
    assert len(set(all_facts)) == len(all_facts)


def test_verifier_selection() -> None:
    n_agents = 10
    # verifier_fraction = 0.3 -> round(0.3 * 10) = 3 verifiers
    world = generate_world(
        seed=55,
        topology="ring",
        harm="split",
        n_agents=n_agents,
        verifier_fraction=0.3,
    )
    expected_count = round(0.3 * n_agents)
    verifiers = world.ground_truth.verifiers
    assert len(verifiers) == expected_count
    assert world.ground_truth.patient_zero not in verifiers

    # Agent seeds match ground truth verifier list
    for agent in world.agents:
        if agent.agent_id in verifiers:
            assert agent.verifier is True
        else:
            assert agent.verifier is False

    # Reproducibility with same seed
    world_repeat = generate_world(
        seed=55,
        topology="ring",
        harm="split",
        n_agents=n_agents,
        verifier_fraction=0.3,
    )
    assert world_repeat.ground_truth.verifiers == verifiers


def test_write_ground_truth_roundtrip_and_line_endings(tmp_path: Path) -> None:
    world = generate_world(seed=77, topology="ring", harm="split")
    gt_path = tmp_path / "gt.json"
    write_ground_truth(world, gt_path)

    raw_bytes = gt_path.read_bytes()
    # No carriage return characters in output
    assert b"\r" not in raw_bytes
    assert raw_bytes.endswith(b"\n")

    decoded_text = raw_bytes.decode("utf-8")
    loaded_gt = GroundTruth.from_json(decoded_text)
    assert loaded_gt == world.ground_truth


def test_argument_validation_value_errors() -> None:
    # n_agents < 6
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="split", n_agents=5)

    # rounds < 1
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="split", rounds=0)

    # verifier_fraction out of bounds [0, 1]
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="split", verifier_fraction=-0.1)
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="split", verifier_fraction=1.1)

    # invalid topology
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="star", harm="split")  # type: ignore[arg-type]

    # invalid harm
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="all")  # type: ignore[arg-type]

    # invalid playbook_style override
    with pytest.raises(ValueError):
        generate_world(seed=1, topology="ring", harm="split", playbook_style=5)
