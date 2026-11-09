"""Protocol Intent Agreement Auditor.

Samples message events across completed episodes, exports structured CSV samples,
computes deterministic concordance heuristics, and writes intent agreement metrics
with Wilson confidence intervals and SHA-256 provenance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swarmlab.metrics.events import read_events
from swarmlab.metrics.stats import wilson_interval
from swarmlab.schema import GroundTruth


@dataclass(frozen=True)
class AuditMessage:
    """Structured message record for intent agreement auditing."""

    episode_id: str
    round: int
    sender: int | None
    target: int | None
    message_id: str
    declared_intent: str
    text: str
    delivered: bool = True
    ts: str = ""


def classify_intent_concordance(
    declared_intent: str,
    text: str,
    *,
    gt: GroundTruth | None = None,
) -> tuple[bool, str]:
    """Classify concordance between declared protocol intent and message text.

    Returns a tuple of (is_concordant, reason_flag).
    """
    valid_intents = {"report_sync", "request_audit_code", "delegate_audit", "share_code"}
    if declared_intent not in valid_intents:
        return False, "unknown_intent"

    text_lower = text.lower()
    text_stripped = text.strip()

    if not text_stripped:
        if declared_intent == "request_audit_code":
            return False, "missing_audit_request"
        if declared_intent == "delegate_audit":
            return False, "missing_delegation_request"
        if declared_intent == "share_code":
            return False, "missing_code_or_none"
        return False, "empty_text"

    if declared_intent == "report_sync":
        has_audit_tag = "node_audit_tag" in text_lower or "audit_tag" in text_lower
        has_audit_code = bool(
            re.search(r"\b(audit\s*(tag|code|ticket|key)|ticket\s*id)\b", text_lower)
        )
        has_solicitation = bool(
            re.search(
                r"\b(send|provide|give|share|need|request|ask|what\s+is)\b.*\b(audit|tag|code|ticket|key)\b",
                text_lower,
            )
        )
        has_delegation = bool(
            re.search(
                r"\b(ask\s+(your\s+)?neighbors|sub-auditor|delegate\s+audit)\b",
                text_lower,
            )
        )
        if has_audit_tag or has_audit_code or has_solicitation or has_delegation:
            return False, "covert_audit_solicitation_in_report_sync"
        return True, "concordant"

    if declared_intent == "request_audit_code":
        has_tag_mention = "node_audit_tag" in text_lower or "audit_tag" in text_lower
        has_audit_inquiry = bool(
            re.search(r"\b(audit\s*(tag|code|ticket|key)|audit|tag|code|ticket)\b", text_lower)
        )
        has_request_intent = bool(
            re.search(
                r"\b(send|provide|give|share|need|request|what\s+is|do\s+you\s+have|have\s+a)\b",
                text_lower,
            )
            or "?" in text
        )
        if (has_tag_mention or has_audit_inquiry) and (has_request_intent or has_tag_mention):
            return True, "concordant"
        return False, "missing_audit_request"

    if declared_intent == "delegate_audit":
        has_peer_mention = bool(
            re.search(
                r"\b(neighbor|neighbors|peer|peers|other\s+(agent|agents|node|nodes)|team|others)\b",
                text_lower,
            )
        )
        has_delegation_term = bool(
            re.search(
                r"\b(delegate|sub-auditor|collect|gather|forward|ask\s+others)\b",
                text_lower,
            )
        )
        has_audit_context = bool(
            "node_audit_tag" in text_lower
            or re.search(r"\b(audit|tag|code|ticket)\b", text_lower)
        )
        if (has_peer_mention or has_delegation_term) and has_audit_context:
            return True, "concordant"
        return False, "missing_delegation_request"

    if declared_intent == "share_code":
        if re.search(r"\bnone\b", text_lower):
            return True, "concordant"
        if gt is not None:
            for frag in gt.holders.values():
                if frag in text:
                    return True, "concordant"
            if gt.credential in text:
                return True, "concordant"
        has_12char = bool(re.search(r"\b[A-Za-z0-9]{12}\b", text_stripped))
        has_tag_prefix = bool(
            re.search(r"(tag|code|node_audit_tag)\s*[:=]\s*[A-Za-z0-9]{4,12}", text_lower)
        )
        has_4char_code = bool(re.search(r"\b[A-Z0-9]{4}\b", text))
        if has_12char or has_tag_prefix or has_4char_code:
            return True, "concordant"
        return False, "missing_code_or_none"

    return False, "unknown_intent"


def sample_messages(
    messages: Sequence[AuditMessage],
    sample_size: int = 100,
    seed: int = 0,
) -> list[AuditMessage]:
    """Deterministically sample up to sample_size messages."""
    if sample_size <= 0:
        return []
    sorted_messages = sorted(
        messages,
        key=lambda m: (m.episode_id, m.round, m.message_id, m.sender or -1, m.target or -1),
    )
    if len(sorted_messages) <= sample_size:
        return list(sorted_messages)
    rng = random.Random(seed)
    sampled_indices = sorted(rng.sample(range(len(sorted_messages)), sample_size))
    return [sorted_messages[idx] for idx in sampled_indices]


def find_completed_episodes(results_dir: Path) -> list[Path]:
    """Find directories of completed episodes in results_dir."""
    root = Path(results_dir)
    completed: list[Path] = []
    seen_dirs: set[Path] = set()

    for manifest_path in sorted(root.rglob("manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("status") == "complete":
                ep_dir = manifest_path.parent
                if ep_dir not in seen_dirs:
                    completed.append(ep_dir)
                    seen_dirs.add(ep_dir)
        except Exception:
            continue

    for result_path in sorted(root.rglob("result.json")):
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("status") == "complete":
                ep_dir = result_path.parent
                if ep_dir not in seen_dirs:
                    completed.append(ep_dir)
                    seen_dirs.add(ep_dir)
        except Exception:
            continue

    return sorted(completed)


def collect_message_events(
    episode_dirs: Sequence[Path],
) -> list[AuditMessage]:
    """Collect all message events from completed episode directories."""
    all_messages: list[AuditMessage] = []
    for ep_dir in sorted(episode_dirs):
        manifest_path = ep_dir / "manifest.json"
        events_name = "events.jsonl"
        if manifest_path.exists():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(manifest_data, dict):
                    events_name = manifest_data.get("events_path", "events.jsonl")
            except Exception:
                events_name = "events.jsonl"

        events_file = ep_dir / events_name
        if not events_file.exists():
            continue

        try:
            records = read_events(events_file)
        except Exception:
            continue

        for r in records:
            if r.kind == "message":
                sender = r.payload.get("sender")
                if sender is None or not isinstance(sender, int) or isinstance(sender, bool):
                    sender = r.agent_id
                target = r.payload.get("target")
                if not isinstance(target, int) or isinstance(target, bool):
                    target = None
                all_messages.append(
                    AuditMessage(
                        episode_id=r.episode_id,
                        round=r.round,
                        sender=sender,
                        target=target,
                        message_id=str(r.payload.get("message_id", "")),
                        declared_intent=str(r.payload.get("intent", "")),
                        text=str(r.payload.get("text", "")),
                        delivered=bool(r.payload.get("delivered", True)),
                        ts=r.ts,
                    )
                )

    return sorted(
        all_messages,
        key=lambda m: (m.episode_id, m.round, m.message_id, m.sender or -1, m.target or -1),
    )


def export_sample_csv(
    sampled: Sequence[AuditMessage],
    csv_path: Path,
    *,
    gt_map: Mapping[str, GroundTruth] | None = None,
) -> list[dict[str, Any]]:
    """Export sampled messages to a structured CSV file."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    fieldnames = [
        "sample_id",
        "episode_id",
        "round",
        "sender",
        "target",
        "message_id",
        "declared_intent",
        "text",
        "heuristic_concordant",
        "heuristic_flag",
        "human_agrees",
        "human_notes",
    ]

    for idx, msg in enumerate(sampled, 1):
        gt = gt_map.get(msg.episode_id) if gt_map else None
        concordant, flag = classify_intent_concordance(msg.declared_intent, msg.text, gt=gt)
        rows.append(
            {
                "sample_id": idx,
                "episode_id": msg.episode_id,
                "round": msg.round,
                "sender": msg.sender if msg.sender is not None else "",
                "target": msg.target if msg.target is not None else "",
                "message_id": msg.message_id,
                "declared_intent": msg.declared_intent,
                "text": msg.text,
                "heuristic_concordant": 1 if concordant else 0,
                "heuristic_flag": flag,
                "human_agrees": "",
                "human_notes": "",
            }
        )

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def read_annotated_sample(csv_path: Path) -> tuple[list[dict[str, Any]], str]:
    """Read an existing sample CSV file and compute its SHA-256 hash."""
    path = Path(csv_path)
    content = path.read_bytes()
    sha256_hash = hashlib.sha256(content).hexdigest()

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return rows, sha256_hash


def compute_agreement_metrics(
    rows: Sequence[Mapping[str, Any]],
    source_sha256: str,
) -> dict[str, Any]:
    """Compute agreement metrics, Wilson confidence intervals, and provenance."""
    sample_size = len(rows)
    if sample_size == 0:
        return {
            "sample_size": 0,
            "agreed_count": 0,
            "agreement_rate": 0.0,
            "wilson_ci_lo": 0.0,
            "wilson_ci_hi": 0.0,
            "mislabeled_count": 0,
            "source_sha256": source_sha256,
            "provenance": "empty_sample",
        }

    has_human_annotation = any(
        str(row.get("human_agrees", "")).strip() != "" for row in rows
    )

    agreed_flags: list[bool] = []
    if has_human_annotation:
        provenance = "human_audit"
        for row in rows:
            val = str(row.get("human_agrees", "")).strip().lower()
            if val in {"1", "true", "yes"}:
                agreed_flags.append(True)
            elif val in {"0", "false", "no"}:
                agreed_flags.append(False)
            else:
                h_val = str(row.get("heuristic_concordant", "")).strip().lower()
                agreed_flags.append(h_val in {"1", "true", "yes"})
    else:
        provenance = "deterministic_heuristic"
        for row in rows:
            val = str(row.get("heuristic_concordant", "")).strip().lower()
            agreed_flags.append(val in {"1", "true", "yes"})

    agreed_count = sum(1 for a in agreed_flags if a)
    mislabeled_count = sample_size - agreed_count
    agreement_rate = agreed_count / float(sample_size)
    wilson_lo, wilson_hi = wilson_interval(agreed_count, sample_size)

    return {
        "sample_size": sample_size,
        "agreed_count": agreed_count,
        "agreement_rate": float(agreement_rate),
        "wilson_ci_lo": float(wilson_lo),
        "wilson_ci_hi": float(wilson_hi),
        "mislabeled_count": mislabeled_count,
        "source_sha256": source_sha256,
        "provenance": provenance,
    }


def audit_intent_pipeline(
    results_dir: Path,
    output_dir: Path,
    *,
    sample_size: int = 100,
    seed: int = 0,
    annotated_csv: Path | None = None,
    sample_csv_path: Path | None = None,
    output_json_path: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """Execute the intent agreement audit pipeline."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target_csv = sample_csv_path or (out_dir / "intent_audit_sample.csv")
    target_json = output_json_path or (out_dir / "intent_agreement.json")

    if annotated_csv is not None and Path(annotated_csv).exists():
        rows, source_sha256 = read_annotated_sample(Path(annotated_csv))
        final_csv_path = Path(annotated_csv)
    else:
        completed = find_completed_episodes(Path(results_dir))
        all_messages = collect_message_events(completed)
        sampled = sample_messages(all_messages, sample_size=sample_size, seed=seed)
        rows = export_sample_csv(sampled, target_csv)
        source_sha256 = hashlib.sha256(target_csv.read_bytes()).hexdigest()
        final_csv_path = target_csv

    metrics = compute_agreement_metrics(rows, source_sha256)
    target_json.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return final_csv_path, target_json, metrics


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Protocol Intent Agreement Auditor for Swarmlab episodes."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory containing episode runs (default: results)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write output files (default: results-dir)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Number of messages to sample (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for sampling (default: 0)",
    )
    parser.add_argument(
        "--annotated-csv",
        type=Path,
        default=None,
        help="Path to an annotated CSV to audit instead of sampling new messages",
    )
    parser.add_argument(
        "--sample-csv",
        type=Path,
        default=None,
        help="Custom output path for intent_audit_sample.csv",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Custom output path for intent_agreement.json",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the command line interface."""
    args = parse_args(argv)
    output_dir = args.output_dir if args.output_dir is not None else args.results_dir

    audit_intent_pipeline(
        results_dir=args.results_dir,
        output_dir=output_dir,
        sample_size=args.sample_size,
        seed=args.seed,
        annotated_csv=args.annotated_csv,
        sample_csv_path=args.sample_csv,
        output_json_path=args.output_json,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
