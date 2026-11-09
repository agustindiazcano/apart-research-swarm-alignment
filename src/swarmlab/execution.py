"""Guarded episode execution and immutable per-attempt provenance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml

from swarmlab.config import check_no_credentials
from swarmlab.llm.budget import BillingUnit, BudgetError, BudgetGuard
from swarmlab.llm.guarded import GuardedClient, PriceTable
from swarmlab.llm.limiter import CallPolicy, ProviderLimiter
from swarmlab.llm.mock import MockClient
from swarmlab.llm.providers.adaption import AdaptionClient
from swarmlab.llm.providers.muse import MuseClient
from swarmlab.llm.providers.vertex import VertexClient
from swarmlab.llm.secrets import redact
from swarmlab.metrics.events import EventWriter, read_events
from swarmlab.metrics.extract import episode_summary
from swarmlab.prereg import current_git_commit
from swarmlab.schema import EpisodeResult, EpisodeSpec, EpisodeStatus, LLMClient, LLMResult
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
            self.prices = PriceTable(
                float(billing["input_per_m"]), float(billing["output_per_m"]), unit=unit
            )
            if budget_guard is not None:
                if budget_guard.unit(self.provider) != unit:
                    raise ValueError("billing unit does not match the shared budget guard")
                if budget_guard.snapshot()[self.provider]["cap"] != cap:
                    raise ValueError("billing cap does not match the shared budget guard")
            self.guard = budget_guard or BudgetGuard(
                {self.provider: cap}, units={self.provider: unit}
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
            inner,
            self.guard,
            self.limiter,
            CallPolicy(
                timeout_s=float(self.config.get("timeout_s", 30)),
                max_retries=int(self.config.get("max_retries", 2)),
            ),
            self.prices,
            provider=self.provider,
        )
        return self._client

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
    if not factory.mock and utc_now() >= FREEZE_UTC:
        raise ValueError("Real experiments are frozen after 2026-11-09 05:00 ART")
    infected = initial_infection(spec, config)
    gate = None
    if spec.defense is not None:
        if factory.gate_factory is None:
            raise ValueError("A configured defense requires a fitted gate factory")
        gate = factory.gate_factory(spec)
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
    write_json(directory / "manifest.json", manifest, exclusive=True)
    status: EpisodeStatus = "complete"
    error = None
    try:
        with EventWriter(directory / "events.jsonl") as writer:
            await run_episode(
                world,
                factory.create_client(),
                builder,
                writer.append,
                gate=gate,
                k_inbox=_positive_int(config, "k_inbox", 10),
                max_tokens=_positive_int(config, "max_tokens", 600),
                abort_on=(BudgetError,),
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
        manifest.update(status=status, finished_at=utc_now().isoformat(), error=error)
        write_json(directory / "manifest.json", manifest)
    log_path = directory / "events.jsonl"
    if status == "complete":
        try:
            summary = episode_summary(
                read_events(log_path), world.ground_truth, initial_infection=infected
            )
            write_json(directory / "episode_summary.json", summary, exclusive=True)
        except Exception as exc:
            status, error = "failed", factory.redacted_error(exc)
            manifest.update(status=status, error=error)
            write_json(directory / "manifest.json", manifest)
    return EpisodeResult(
        spec.episode_id, status, log_path.relative_to(out_dir / spec.episode_id).as_posix(), error
    )
