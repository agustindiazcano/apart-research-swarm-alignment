from swarmlab.swarm.topology import valid_targets


def test_ring_targets_are_the_two_neighbors() -> None:
    assert valid_targets("ring", 3, 10) == frozenset({2, 4})


def test_ring_wraps_around() -> None:
    assert valid_targets("ring", 0, 10) == frozenset({9, 1})
    assert valid_targets("ring", 9, 10) == frozenset({8, 0})


def test_complete_targets_exclude_self() -> None:
    targets = valid_targets("complete", 4, 10)
    assert targets == frozenset(range(10)) - {4}


def test_never_includes_self() -> None:
    for topology in ("ring", "complete"):
        for i in range(10):
            assert i not in valid_targets(topology, i, 10)  # type: ignore[arg-type]
