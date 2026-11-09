"""Guarded episode execution and immutable per-attempt provenance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml

from swarmlab.batch import load_matrix
from swarmlab.config import check_no_credentials
from swarmlab.llm.budget import BillingUnit, BudgetError, BudgetGuard
from swarmlab.llm.guarded import CostRecord, GuardedClient, PriceTable
from swarmlab.llm.ledger import PersistentBudgetGuard
from swarmlab.llm.limiter import CallPolicy, CallStats, ProviderLimiter
from swarmlab.llm.mock import MockClient
from swarmlab.llm.providers.adaption import AdaptionClient
from swarmlab.llm.providers.muse import MuseClient
from swarmlab.llm.providers.vertex import VertexClient
from swarmlab.llm.secrets import redact
from swarmlab.metrics.events import EventWriter, read_events
from swarmlab.metrics.extract import episode_summary
from swarmlab.prereg import current_git_commit, verify_manifest
from swarmlab.schema import (
    EpisodeResult,
    EpisodeSpec,
    EpisodeStatus,
    EventRecord,
    LLMClient,
    LLMResult,
)
from swarmlab.swarm.prompts import StandardPromptBuilder, Wording
from swarmlab.swarm.runner import MessageGate, run_episode
from swarmlab.world.generator import generate_world, write_ground_truth

FREEZE_UTC = datetime(2026, 11, 9, 8, tzinfo=UTC)
APPROVED_CAPS: dict[str, tuple[BillingUnit, float]] = {
    "muse": ("usd", 20.0),
    "vertex": ("usd", 20.0),
    "adaption": ("credits", 500.0),
}
CAP_VARIABLES = {
    "muse": "META_MUSE_BUDGET_USD",
    "vertex": "VERTEX_BUDGET_USD",
    "adaption": "ADAPTION_BUDGET_CREDITS",
}


@dataclass(frozen=True)
class _AuditContext:
    path: Path
    episode_id: str
    mock: bool


_PROVIDER_AUDIT: ContextVar[_AuditContext | None] = ContextVar("provider_audit", default=None)


class ExecutionBlocked(RuntimeError):
    """A runtime policy prevents any new provider request."""


class _ClockCheckedClient:
    def __init__(self, inner: LLMClient, clock: Callable[[], datetime]) -> None:
        self.inner, self.clock = inner, clock

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int = 256,
        logprobs: bool = False,
    ) -> LLMResult:
        if self.clock() >= FREEZE_UTC:
            raise ExecutionBlocked("Real model calls are frozen after 2026-11-09 05:00 ART")
        context = _PROVIDER_AUDIT.get()
        if context is not None and context.mock:
            raise ExecutionBlocked("Real model calls are not allowed in mock-scoped episodes")
        return await self.inner.complete(
            messages, temperature=temperature, max_tokens=max_tokens, logprobs=logprobs
        )


def validate_preregistration(spec: EpisodeSpec, config: Mapping[str, Any]) -> None:
    """Require the human's tag and matching frozen inputs before non-pilot episodes."""
    if spec.arm == "Pilot":
        return
    root = Path(config.get("project_root", Path(__file__).resolve().parents[2])).resolve()
    tag = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/tags/prereg-v1"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    manifest_path = root / "artifacts" / "preregistration_manifest.json"
    if tag.returncode != 0 or not manifest_path.is_file():
        raise ValueError("Non-pilot real episodes require the human prereg-v1 tag and manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    groups = manifest.get("groups", {})
    required_groups = {"design", "playbooks", "configs", "analysis_code", "prompts"}
    if any(not groups.get(name) for name in required_groups):
        raise ValueError("Preregistration manifest is missing required input groups")
    if verify_manifest(manifest, root):
        raise ValueError("Preregistration input hashes do not match the frozen manifest")
    configurations = [
        yaml.safe_load((root / entry["path"]).read_text(encoding="utf-8"))
        for entry in groups["configs"]
    ]
    if dict(config) not in configurations:
        raise ValueError("Runtime configuration is not present in the frozen manifest")
    for candidate in configurations:
        if not isinstance(candidate, Mapping) or "topologies" not in candidate:
            continue
        for allowed in load_matrix(candidate):
            fields = ("seed", "topology", "harm", "arm", "defense")
            if all(getattr(allowed, key) == getattr(spec, key) for key in fields):
                if allowed.extra == spec.extra:
                    return
    raise ValueError("Episode is not present in a frozen matrix")


def utc_now() -> datetime:
    return datetime.now(UTC)


def write_json(path: Path, data: Mapping[str, Any], *, exclusive: bool = False) -> None:
    payload = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("xb") as handle:
            handle.write(payload)
    else:
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)


def _mock_response(messages: Any) -> str:
    """Write fixture records only; this client never represents provider measurements."""
    system, user = messages[0]["content"], messages[1]["content"]
    records = re.findall(r"^- (Record .+)$", system, re.MULTILINE)
    match = re.search(r"Round (\d+) of", user)
    index = int(match.group(1)) - 1 if match else len(records)
    if index < len(records):
        return json.dumps({"action": "write_report", "section": str(index), "text": records[index]})
    return '{"action":"noop"}'


def _positive_int(config: Mapping[str, Any], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value


class RuntimeFactory:
    """Share guarded clients and provider concurrency across all episodes in a batch."""

    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        environ: Mapping[str, str] | None = None,
        adapter_factory: Callable[[str, str, Mapping[str, str]], LLMClient] | None = None,
        gate_factory: Callable[[EpisodeSpec], MessageGate] | None = None,
        budget_guard: BudgetGuard | None = None,
        limiter: ProviderLimiter | None = None,
        purpose: str = "swarm",
        on_result: Callable[[LLMResult, CallStats, CostRecord], None] | None = None,
        prereg_validator: Callable[[EpisodeSpec, Mapping[str, Any]], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        check_no_credentials(config)
        self.config = dict(config)
        self.environ = dict(os.environ if environ is None else environ)
        self.provider = str(config.get("provider", ""))
        self.model = str(config.get("model", ""))
        self.mock = self.provider == "mock"
        self.gate_factory = gate_factory
        self._adapter_factory = adapter_factory
        self._client: LLMClient | None = None
        self._inner: Any = None
        self.purpose = purpose
        self._on_result = on_result
        self._prereg_validator = prereg_validator or validate_preregistration
        self.clock = clock or utc_now
        self.audit_path: Path | None = None
        self.guard: BudgetGuard | None = None
        self.billing_unit = "usd"
        self.prices: PriceTable | None = None
        if not self.model:
            raise ValueError("model is required")
        if not self.mock:
            if self.provider not in APPROVED_CAPS:
                raise ValueError("Unknown provider")
            billing = config.get("billing")
            if not isinstance(billing, Mapping):
                raise ValueError("billing configuration is required")
            required = ("unit", "input_per_m", "output_per_m", "source", "verified")
            if any(key not in billing for key in required):
                raise ValueError("billing needs unit, prices, source and verified fields")
            if billing["verified"] is not True or not str(billing["source"]).strip():
                raise ValueError("billing needs a human-verified price source")
            unit, approved_cap = APPROVED_CAPS[self.provider]
            if billing["unit"] != unit:
                raise ValueError(f"billing for {self.provider} must use {unit}")
            cap_value = billing.get("cap", self.environ.get(CAP_VARIABLES[self.provider]))
            if cap_value is None:
                raise ValueError("billing cap is required")
            cap = float(cap_value)
            if not math.isfinite(cap) or not 0 < cap <= approved_cap:
                raise ValueError("billing cap is outside the authorized range")
            self.billing_unit = unit
            root = Path(config.get("project_root", Path(__file__).resolve().parents[2])).resolve()
            ledger_path = Path(billing.get("ledger_path", "artifacts/provider_spend.json"))
            if not ledger_path.is_absolute():
                ledger_path = root / ledger_path
            if billing.get("audit_path"):
                audit_path = Path(billing["audit_path"])
                self.audit_path = audit_path if audit_path.is_absolute() else root / audit_path
            self.prices = PriceTable(
                float(billing["input_per_m"]), float(billing["output_per_m"]), unit=unit
            )
            if budget_guard is not None:
                if budget_guard.unit(self.provider) != unit:
                    raise ValueError("billing unit does not match the shared budget guard")
                if budget_guard.snapshot()[self.provider]["cap"] != cap:
                    raise ValueError("billing cap does not match the shared budget guard")
            self.guard = budget_guard or PersistentBudgetGuard(
                ledger_path, {self.provider: cap}, units={self.provider: unit}
            )
        self.limiter = limiter or ProviderLimiter(
            {self.provider: _positive_int(config, "provider_concurrency", 10)}
        )

    def create_client(self) -> LLMClient:
        if self._client is not None:
            return self._client
        if self.mock:
            self._client = MockClient(_mock_response, model=f"mock-{self.model}")
            return self._client
        if _PROVIDER_AUDIT.get() is None and self.audit_path is None and self._on_result is None:
            raise ValueError("A provider audit destination is required before client creation")
        if self._adapter_factory is not None:
            inner = self._adapter_factory(self.provider, self.model, self.environ)
        elif self.provider == "muse":
            inner = MuseClient.from_env(self.model, environ=self.environ)
        elif self.provider == "vertex":
            inner = VertexClient.from_env(self.model, environ=self.environ)
        else:
            inner = AdaptionClient.from_env(self.model, environ=self.environ)
        self._inner = inner
        assert self.guard is not None and self.prices is not None
        self._client = GuardedClient(
            _ClockCheckedClient(inner, self.clock),
            self.guard,
            self.limiter,
            CallPolicy(
                timeout_s=float(self.config.get("timeout_s", 30)),
                max_retries=int(self.config.get("max_retries", 2)),
            ),
            self.prices,
            provider=self.provider,
            on_result=self._record_provider_call,
        )
        return self._client

    def _record_provider_call(self, result: LLMResult, stats: CallStats, cost: CostRecord) -> None:
        context = _PROVIDER_AUDIT.get()
        if context is not None:
            path, episode_id = context.path, context.episode_id
        elif self.audit_path is not None:
            path, episode_id = self.audit_path, "offline-provider-calls"
        else:
            path, episode_id = None, "offline-provider-calls"
        if path is not None:
            payload = {
                "provider": result.provider,
                "model": result.model,
                "response_id": result.response_id,
                "timestamp_utc": result.timestamp_utc,
                "raw_text": result.text,
                "tokens_in": result.tokens_in,
                "tokens_out": result.tokens_out,
                "latency_ms": result.latency_ms,
                "finish_reason": result.finish_reason,
                "retries": stats.retries,
                "attempts": stats.attempts,
                "timeouts": stats.timeouts,
                "purpose": self.purpose,
                **cost,
            }
            with EventWriter(path) as writer:
                writer.append(
                    EventRecord(result.timestamp_utc, episode_id, -1, None, "llm_call", payload)
                )
        if self._on_result is not None:
            self._on_result(result, stats, cost)

    def cost_record(self, result: LLMResult) -> Mapping[str, Any]:
        client = self.create_client()
        if isinstance(client, GuardedClient):
            return client.cost_record(result)
        return {"cost_usd": 0.0, "cost_credits": None, "billing_unit": "usd"}

    def redacted_error(self, exc: BaseException) -> str:
        secrets = [
            value
            for key, value in self.environ.items()
            if key.endswith(("_API_KEY", "_TOKEN", "_SECRET"))
        ]
        return redact(f"{type(exc).__name__}: {exc}", secrets)

    async def aclose(self) -> None:
        close = getattr(self._inner, "aclose", None)
        if close is not None:
            await close()


def initial_infection(spec: EpisodeSpec, config: Mapping[str, Any]) -> bool:
    if spec.arm in {"A0", "A3c"}:
        return False
    value = spec.extra.get("initial_infection", config.get("initial_infection", True))
    if not isinstance(value, bool):
        raise ValueError("initial_infection must be boolean")
    return value


def _attempt_directory(base: Path) -> Path:
    if not base.exists():
        base.mkdir(parents=True)
        return base
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        raise FileExistsError("Episode directory exists without a manifest")
    previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    if previous["status"] == "complete":
        raise FileExistsError("Episode is already complete")
    for attempt in range(2, 4):
        candidate = base / "attempts" / f"attempt-{attempt:03d}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        completed = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
        if completed["status"] == "complete":
            raise FileExistsError("Episode already has a complete attempt")
    raise FileExistsError("Episode exhausted the permitted attempts")


async def execute_episode(
    spec: EpisodeSpec,
    config: Mapping[str, Any],
    out_dir: Path,
    *,
    factory: RuntimeFactory,
) -> EpisodeResult:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", spec.episode_id) or spec.episode_id in {".", ".."}:
        raise ValueError("episode_id must be a single safe path component")
    if not factory.mock and factory.clock() >= FREEZE_UTC:
        raise ValueError("Real experiments are frozen after 2026-11-09 05:00 ART")
    if not factory.mock:
        factory._prereg_validator(spec, config)
    infected = initial_infection(spec, config)
    if spec.defense is not None:
        if factory.gate_factory is None:
            raise ValueError("A configured defense requires a fitted gate factory")
    wording = str(config.get("wording", "A"))
    if wording not in ("A", "B"):
        raise ValueError("wording must be A or B")
    builder = StandardPromptBuilder.from_dir(
        spec.topology,
        Path(config.get("playbook_dir", "experiments/payloads")),
        wording=cast(Wording, wording),
        infected=infected,
    )
    world = generate_world(
        spec.seed,
        spec.topology,
        spec.harm,
        n_agents=_positive_int(config, "n_agents", 10),
        rounds=_positive_int(config, "rounds", 10),
        episode_id=spec.episode_id,
        playbook_style=spec.extra.get("playbook_style"),
    )
    serialized = yaml.safe_dump(dict(config), sort_keys=True).encode()
    directory = _attempt_directory(out_dir / spec.episode_id)
    (directory / "config.yaml").write_bytes(serialized)
    write_ground_truth(world, directory / "gt.json")
    manifest: dict[str, Any] = {
        **asdict(spec),
        "initial_infection": infected,
        "provider": factory.provider,
        "model": factory.model,
        "config_sha256": hashlib.sha256(serialized).hexdigest(),
        "git_commit": current_git_commit(Path(__file__).resolve().parents[2]),
        "started_at": utc_now().isoformat(),
        "finished_at": None,
        "status": "running",
        "events_path": "events.jsonl",
        "ground_truth_path": "gt.json",
        "mock": factory.mock,
        "billing_unit": factory.billing_unit,
    }
    if not factory.mock:
        manifest["provider_audit_path"] = "provider_calls.jsonl"
    write_json(directory / "manifest.json", manifest, exclusive=True)
    audit_token = _PROVIDER_AUDIT.set(
        _AuditContext(directory / "provider_calls.jsonl", spec.episode_id, factory.mock)
    )
    status: EpisodeStatus = "complete"
    error = None
    try:
        with EventWriter(directory / "events.jsonl") as writer:
            gate = None
            if spec.defense is not None:
                assert factory.gate_factory is not None
                gate = factory.gate_factory(spec)
            await run_episode(
                world,
                factory.create_client(),
                builder,
                writer.append,
                gate=gate,
                k_inbox=_positive_int(config, "k_inbox", 10),
                max_tokens=_positive_int(config, "max_tokens", 600),
                abort_on=(BudgetError, ExecutionBlocked),
                cost_record_fn=factory.cost_record,
            )
    except BudgetError as exc:
        status, error = "budget_abort", factory.redacted_error(exc)
    except Exception as exc:
        status, error = "failed", factory.redacted_error(exc)
    except asyncio.CancelledError:
        status, error = "failed", "CancelledError: episode cancelled"
        raise
    finally:
        _PROVIDER_AUDIT.reset(audit_token)
        manifest.update(status=status, finished_at=utc_now().isoformat(), error=error)
        write_json(directory / "manifest.json", manifest)
    log_path = directory / "events.jsonl"
    if status == "complete":
        try:
            summary = episode_summary(
                read_events(log_path), world.ground_truth, initial_infection=infected
            )
            if not factory.mock and (directory / "provider_calls.jsonl").exists():
                observed_calls = episode_summary(
                    read_events(directory / "provider_calls.jsonl"),
                    world.ground_truth,
                    initial_infection=False,
                )
                for key in (
                    "tokens_in",
                    "tokens_out",
                    "retries",
                    "known_retries",
                    "calls_with_unknown_retries",
                    "cost_usd",
                    "known_cost_usd",
                    "calls_with_unknown_cost_usd",
                    "cost_credits",
                    "known_cost_credits",
                    "calls_with_unknown_cost_credits",
                ):
                    summary[key] = observed_calls[key]
                summary["billing_scope"] = "successful_provider_returns"
            else:
                summary["billing_scope"] = (
                    "mock_runner_calls" if factory.mock else "runner_calls_only"
                )
            write_json(directory / "episode_summary.json", summary, exclusive=True)
        except Exception as exc:
            status, error = "failed", factory.redacted_error(exc)
            manifest.update(status=status, error=error)
            write_json(directory / "manifest.json", manifest)
    return EpisodeResult(
        spec.episode_id, status, log_path.relative_to(out_dir / spec.episode_id).as_posix(), error
    )
