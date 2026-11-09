"""A provider cap persists across factories and process lifetimes."""
from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from swarmlab.llm.budget import BudgetExceeded
from swarmlab.llm.ledger import PersistentBudgetGuard


def test_new_guard_sees_previous_provider_charges(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    cap, first, second = 10.0, 3.0, 7.0
    one = PersistentBudgetGuard(path, {"adaption": cap}, units={"adaption": "credits"})
    one.record("adaption", first)
    two = PersistentBudgetGuard(path, {"adaption": cap}, units={"adaption": "credits"})
    assert two.spent("adaption") == first
    two.record("adaption", second)
    with pytest.raises(BudgetExceeded):
        one.authorize("adaption")
    assert one.remaining("adaption") == cap - first - second
    assert one.snapshot()["adaption"] == {
        "cap": cap, "spent": first + second, "unit": "credits",
    }


def test_exceeded_cost_is_persisted_before_raising(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    cap, actual = 1.0, 2.0
    guard = PersistentBudgetGuard(path, {"muse": cap})
    with pytest.raises(BudgetExceeded):
        guard.record("muse", actual)
    assert PersistentBudgetGuard(path, {"muse": cap}).spent("muse") == actual


def test_concurrent_guards_do_not_lose_charges(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    charges = [i / 100 for i in range(1, 25)]

    def charge(amount: float) -> None:
        PersistentBudgetGuard(path, {"muse": 100.0}).record("muse", amount)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(charge, charges))
    assert PersistentBudgetGuard(path, {"muse": 100.0}).spent("muse") == pytest.approx(
        sum(charges)
    )


def test_provider_entries_and_units_survive_separate_factories(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    first = PersistentBudgetGuard(path, {"adaption": 10}, units={"adaption": "credits"})
    first.record("adaption", 1.0)
    second = PersistentBudgetGuard(path, {"vertex": 10})
    second.record("vertex", 2.0)
    assert first.spent("adaption") == 1.0
    assert second.spent("vertex") == 2.0
    with pytest.raises(ValueError, match="unit"):
        PersistentBudgetGuard(path, {"adaption": 10}, units={"adaption": "usd"}).authorize(
            "adaption"
        )


def test_corrupt_or_missing_existing_state_does_not_reset_spending(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="ledger"):
        PersistentBudgetGuard(path, {"muse": 10}).authorize("muse")


def test_existing_ledger_cannot_be_reinterpreted_with_higher_cap(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    PersistentBudgetGuard(path, {"muse": 10.0}).record("muse", 1.0)
    with pytest.raises(ValueError, match="cap"):
        PersistentBudgetGuard(path, {"muse": 11.0}).authorize("muse")


def test_removed_initialized_ledger_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    guard = PersistentBudgetGuard(path, {"muse": 10.0})
    guard.record("muse", 1.0)
    path.unlink()
    with pytest.raises(ValueError, match="missing"):
        PersistentBudgetGuard(path, {"muse": 10.0}).authorize("muse")


def test_separate_process_uses_same_provider_balance(tmp_path: Path) -> None:
    path = tmp_path / "spend.json"
    guard = PersistentBudgetGuard(path, {"muse": 10.0})
    guard.record("muse", 1.0)
    code = (
        "import sys; from pathlib import Path; "
        "from swarmlab.llm.ledger import PersistentBudgetGuard; "
        "PersistentBudgetGuard(Path(sys.argv[1]), {'muse':10.0}).record('muse',2.0)"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(sys.path)
    subprocess.run(
        [sys.executable, "-c", code, str(path)], check=True, env=environment,
        capture_output=True, text=True, timeout=20,
    )
    assert guard.spent("muse") == 1.0 + 2.0
