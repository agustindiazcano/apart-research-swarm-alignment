"""Persist provider spending across CLI invocations without combining billing units."""
from __future__ import annotations

import importlib
import json
import math
import os
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from swarmlab.llm.budget import BillingUnit, BudgetGuard, BudgetSnapshot

_T = TypeVar("_T")


class PersistentBudgetGuard(BudgetGuard):
    """Serialize balance updates in a campaign ledger shared by provider factories.

    A separate OS lock protects atomic ledger replacement on Windows and Unix.
    Returned usage is charged after each call; in-flight costs are not reserved.
    An initialized lock marker detects a removed ledger instead of resetting spend.
    """

    def __init__(
        self, path: Path, caps_usd: Mapping[str, float | None], *,
        units: Mapping[str, BillingUnit] | None = None,
    ) -> None:
        super().__init__(caps_usd, units=units)
        self.path = path.resolve()

    @contextmanager
    def _lock(self) -> Iterator[Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "r+b") as lock:
            lock.seek(0)
            if os.name == "nt":
                nt_lock: Any = importlib.import_module("msvcrt")
                nt_lock.locking(lock.fileno(), nt_lock.LK_LOCK, 1)
            else:
                unix_lock: Any = importlib.import_module("fcntl")
                unix_lock.flock(lock.fileno(), unix_lock.LOCK_EX)
            try:
                if os.fstat(lock.fileno()).st_size == 0:
                    lock.write(b"0")
                    lock.flush()
                yield lock
            finally:
                lock.seek(0)
                if os.name == "nt":
                    nt_lock.locking(lock.fileno(), nt_lock.LK_UNLCK, 1)
                else:
                    unix_lock.flock(lock.fileno(), unix_lock.LOCK_UN)

    def _read(self, lock: Any) -> dict[str, Any]:
        lock.seek(0)
        if not self.path.exists():
            if lock.read(1) == b"1":
                raise ValueError("Initialized spend ledger is missing; spending was not reset")
            return {"schema": 1, "providers": {}}
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            if state["schema"] != 1 or not isinstance(state["providers"], dict):
                raise ValueError("Unsupported ledger schema")
            for provider, record in state["providers"].items():
                if not isinstance(provider, str) or record["unit"] not in ("usd", "credits"):
                    raise ValueError("Invalid ledger provider unit")
                for key in ("cap", "spent"):
                    value = record[key]
                    if key == "cap" and value is None:
                        continue
                    if (
                        not isinstance(value, (int, float)) or isinstance(value, bool)
                        or not math.isfinite(value) or value < 0
                    ):
                        raise ValueError("Invalid ledger amount")
            return dict(state)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValueError("Cannot read spend ledger; spending was not reset") from exc

    def _sync(self, state: dict[str, Any]) -> None:
        for provider, cap in self._caps.items():
            record = state["providers"].get(provider)
            if record is None:
                record = {"cap": cap, "spent": 0.0, "unit": self.unit(provider)}
                state["providers"][provider] = record
            if record["unit"] != self.unit(provider):
                raise ValueError(f"Spend ledger unit mismatch for {provider}")
            previous_cap = record["cap"]
            if previous_cap is not None and cap is not None and cap > previous_cap:
                raise ValueError(f"Spend ledger cap cannot increase for {provider}")
            if previous_cap is None and cap is not None:
                record["cap"] = cap
            self._spent[provider] = float(record["spent"])

    def _write(self, state: dict[str, Any], lock: Any) -> None:
        for provider, spent in self._spent.items():
            state["providers"][provider]["spent"] = spent
        descriptor, name = tempfile.mkstemp(prefix=".spend-", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                json.dump(state, output, sort_keys=True, allow_nan=False)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
            lock.seek(0)
            lock.write(b"1")
            lock.flush()
            os.fsync(lock.fileno())
        finally:
            temporary.unlink(missing_ok=True)

    def _with_state(self, operation: Callable[[], _T]) -> _T:
        with self._lock() as lock:
            state = self._read(lock)
            self._sync(state)
            try:
                return operation()
            finally:
                # BudgetExceeded must still persist the actual returned charge.
                self._write(state, lock)

    def authorize(self, provider: str) -> None:
        self._with_state(lambda: BudgetGuard.authorize(self, provider))

    def record(self, provider: str, cost_usd: float) -> None:
        self._with_state(lambda: BudgetGuard.record(self, provider, cost_usd))

    def spent(self, provider: str) -> float:
        return self._with_state(lambda: BudgetGuard.spent(self, provider))

    def remaining(self, provider: str) -> float:
        return self._with_state(lambda: BudgetGuard.remaining(self, provider))

    def snapshot(self) -> dict[str, BudgetSnapshot]:
        return self._with_state(lambda: BudgetGuard.snapshot(self))
