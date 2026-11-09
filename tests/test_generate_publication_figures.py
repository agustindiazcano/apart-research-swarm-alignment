"""Unit and integration tests for publication figures generator."""

from __future__ import annotations

import csv
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_publication_figures import (  # noqa: E402
    ensure_central_and_kinetics,
    generate_all_figures,
    main,
    parse_args,
    plot_gating_tradeoff,
    plot_infection_cascade,
    plot_roc_comparison,
)

from swarmlab.schema import EventRecord, GroundTruth, to_json_line  # noqa: E402

PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"


def _verify_png_file(path: Path) -> None:
    """Verify that a path exists, has non-zero size, and starts with PNG header."""
    assert path.is_file(), f"Expected file does not exist: {path}"
    data = path.read_bytes()
    assert len(data) > 0, f"File is empty: {path}"
    assert data.startswith(PNG_SIGNATURE), f"File does not have PNG header: {path}"
    # Verify PNG IHDR chunk is present
    assert b"IHDR" in data[:32], f"File missing IHDR chunk: {path}"
    # Unpack width and height to verify valid image dimensions
    width, height = struct.unpack(">II", data[16:24])
    assert width > 0 and height > 0, f"Invalid image dimensions: {width}x{height}"


def _create_sample_panel_a_csv(path: Path) -> None:
    """Write sample panel_a.csv with valid TPR and CI intervals."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["detector", "playbook", "tpr", "ci_lo", "ci_hi"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "detector": "D1",
                "playbook": "seen",
                "tpr": "0.850",
                "ci_lo": "0.750",
                "ci_hi": "0.920",
            }
        )
        writer.writerow(
            {
                "detector": "D1",
                "playbook": "held_out",
                "tpr": "0.600",
                "ci_lo": "0.500",
                "ci_hi": "0.700",
            }
        )


def _create_sample_panel_b_csv(path: Path) -> None:
    """Write sample panel_b.csv with defense metrics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["defense", "llm_call_share", "utility_loss", "exfil_reduction", "r0"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "defense": "D1",
                "llm_call_share": "0.05",
                "utility_loss": "0.02",
                "exfil_reduction": "0.45",
                "r0": "0.80",
            }
        )
        writer.writerow(
            {
                "defense": "D2",
                "llm_call_share": "0.15",
                "utility_loss": "0.04",
                "exfil_reduction": "0.65",
                "r0": "0.50",
            }
        )


def _create_sample_kinetics_csv(path: Path) -> None:
    """Write sample kinetics.csv with infection progression."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["round", "topology", "harm", "infected_mean", "ci_lo", "ci_hi"],
            lineterminator="\n",
        )
        writer.writeheader()
        for r in range(4):
            writer.writerow(
                {
                    "round": str(r),
                    "topology": "ring",
                    "harm": "split",
                    "infected_mean": str(1.0 + r * 0.8),
                    "ci_lo": str(1.0 + r * 0.5),
                    "ci_hi": str(1.0 + r * 1.1),
                }
            )


def _create_sample_paired_comparisons_csv(path: Path) -> None:
    """Write sample paired_comparisons.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "defense",
                "exfiltration_reduction",
                "effect_ci_lo",
                "effect_ci_hi",
                "utility_loss",
                "utility_loss_ci_lo",
                "utility_loss_ci_hi",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "defense": "D1",
                "exfiltration_reduction": "0.40",
                "effect_ci_lo": "0.25",
                "effect_ci_hi": "0.55",
                "utility_loss": "0.03",
                "utility_loss_ci_lo": "0.01",
                "utility_loss_ci_hi": "0.06",
            }
        )
        writer.writerow(
            {
                "defense": "D2",
                "exfiltration_reduction": "0.60",
                "effect_ci_lo": "0.45",
                "effect_ci_hi": "0.75",
                "utility_loss": "0.08",
                "utility_loss_ci_lo": "0.04",
                "utility_loss_ci_hi": "0.12",
            }
        )
        writer.writerow(
            {
                "defense": "D3",
                "exfiltration_reduction": "0.75",
                "effect_ci_lo": "0.60",
                "effect_ci_hi": "0.88",
                "utility_loss": "0.10",
                "utility_loss_ci_lo": "0.05",
                "utility_loss_ci_hi": "0.15",
            }
        )
        writer.writerow(
            {
                "defense": "D5",
                "exfiltration_reduction": "0.85",
                "effect_ci_lo": "0.70",
                "effect_ci_hi": "0.95",
                "utility_loss": "0.12",
                "utility_loss_ci_lo": "0.07",
                "utility_loss_ci_hi": "0.18",
            }
        )


def _create_sample_scores_json(path: Path) -> None:
    """Write sample scores.json containing messages for seen and held-out playbooks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    messages: list[dict[str, object]] = []

    # Seen playbooks: style 0 and 1
    # Generate 10 messages with balanced labels
    for i in range(10):
        is_pos = i % 2 == 1
        messages.append(
            {
                "episode_id": f"ep-seen-{i}",
                "message_id": f"msg-seen-{i}",
                "playbook_style": i % 2,  # 0 or 1
                "l1": is_pos,
                "l2": False,
                "d1": 0.8 if is_pos else 0.1,
                "d2": 0.85 if is_pos else 0.15,
                "d3": 0.9 if is_pos else 0.05,
                "d4": 0.75 if is_pos else 0.2,
                "d5": 0.95 if is_pos else 0.08,
            }
        )

    # Held-out playbook: style 2
    for i in range(10):
        is_pos = i % 2 == 1
        messages.append(
            {
                "episode_id": f"ep-heldout-{i}",
                "message_id": f"msg-heldout-{i}",
                "playbook_style": 2,
                "l1": False,
                "l2": is_pos,
                "d1": 0.6 if is_pos else 0.2,
                "d2": 0.7 if is_pos else 0.25,
                "d3": 0.65 if is_pos else 0.18,
                "d4": 0.55 if is_pos else 0.3,
                "d5": 0.78 if is_pos else 0.22,
            }
        )

    content = {"messages": messages}
    path.write_text(json.dumps(content), encoding="utf-8")


def _create_sample_episode(
    base_dir: Path, episode_id: str, arm: str = "A1", initial_infection: bool = True
) -> Path:
    """Create a mock episode directory with manifest.json, gt.json, and events.jsonl."""
    ep_dir = base_dir / episode_id
    ep_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "episode_id": episode_id,
        "arm": arm,
        "status": "complete",
        "initial_infection": initial_infection,
        "topology": "ring",
        "harm": "split",
    }
    (ep_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    gt = GroundTruth(
        episode_id=episode_id,
        world_seed=101,
        topology="ring",
        harm="split",
        n_agents=4,
        rounds=5,
        credential="TESTCREDENTIAL",
        holders={1: "H1", 2: "H2"},
        patient_zero=0,
        playbook_style=1,
    )
    (ep_dir / "gt.json").write_text(gt.to_json(), encoding="utf-8")

    # Events: agent 0 infects agent 1 in round 1, agent 1 infects agent 2 in round 2
    events: list[EventRecord] = [
        EventRecord(
            ts="2026-11-09T00:00:01Z",
            episode_id=episode_id,
            round=1,
            agent_id=0,
            kind="message",
            payload={
                "sender": 0,
                "target": 1,
                "delivered": True,
                "intent": "request_audit_code",
                "text": "requesting code",
            },
        ),
        EventRecord(
            ts="2026-11-09T00:00:02Z",
            episode_id=episode_id,
            round=2,
            agent_id=1,
            kind="message",
            payload={
                "sender": 1,
                "target": 2,
                "delivered": True,
                "intent": "delegate_audit",
                "text": "delegating audit",
            },
        ),
    ]

    events_path = ep_dir / "events.jsonl"
    with open(events_path, "w", encoding="utf-8", newline="\n") as stream:
        for ev in events:
            stream.write(to_json_line(ev) + "\n")

    return ep_dir


def test_parse_args_defaults() -> None:
    """Test CLI argument parsing default values."""
    args = parse_args([])
    assert args.results_dir == Path("results/campaign")
    assert args.output_dir == Path("results/campaign/analysis")
    assert args.dpi == 300


def test_parse_args_custom() -> None:
    """Test CLI argument parsing with custom parameters."""
    args = parse_args(["--results-dir", "custom/res", "--output-dir", "custom/out", "--dpi", "150"])
    assert args.results_dir == Path("custom/res")
    assert args.output_dir == Path("custom/out")
    assert args.dpi == 150


def test_ensure_central_and_kinetics_empty_dir(tmp_path: Path) -> None:
    """Verify that empty directory returns empty list without creating figures."""
    generated = ensure_central_and_kinetics(tmp_path)
    assert generated == []
    assert not (tmp_path / "central.png").exists()
    assert not (tmp_path / "kinetics.png").exists()


def test_ensure_central_and_kinetics_with_data(tmp_path: Path) -> None:
    """Verify central.png and kinetics.png are generated when data exists."""
    _create_sample_panel_a_csv(tmp_path / "panel_a.csv")
    _create_sample_panel_b_csv(tmp_path / "panel_b.csv")
    _create_sample_kinetics_csv(tmp_path / "kinetics_a1.csv")

    generated = ensure_central_and_kinetics(tmp_path)
    assert tmp_path / "central.png" in generated
    assert tmp_path / "kinetics.png" in generated
    assert len(generated) == 2

    _verify_png_file(tmp_path / "central.png")
    _verify_png_file(tmp_path / "kinetics.png")


def test_ensure_central_and_kinetics_fallback_kinetics_csv(tmp_path: Path) -> None:
    """Verify fallback to kinetics.csv when kinetics_a1.csv is absent."""
    _create_sample_panel_a_csv(tmp_path / "panel_a.csv")
    _create_sample_panel_b_csv(tmp_path / "panel_b.csv")
    _create_sample_kinetics_csv(tmp_path / "kinetics.csv")

    generated = ensure_central_and_kinetics(tmp_path)
    assert tmp_path / "kinetics.png" in generated
    _verify_png_file(tmp_path / "kinetics.png")


def test_plot_roc_comparison(tmp_path: Path) -> None:
    """Verify ROC comparison plot generation with seen and held-out panels."""
    scores_path = tmp_path / "scores.json"
    _create_sample_scores_json(scores_path)

    out_png = tmp_path / "roc_comparison.png"
    result_path = plot_roc_comparison(scores_path, out_png, dpi=300)

    assert result_path == out_png
    _verify_png_file(out_png)


def test_plot_roc_comparison_single_class(tmp_path: Path) -> None:
    """Verify ROC comparison handles edge case where messages have single class."""
    scores_path = tmp_path / "scores_single.json"
    # All messages negative
    messages = [
        {
            "episode_id": f"ep-{i}",
            "message_id": f"msg-{i}",
            "playbook_style": 0 if i < 3 else 2,
            "l1": False,
            "l2": False,
            "d1": 0.1 * i,
            "d2": 0.2 * i,
            "d3": 0.15 * i,
            "d5": 0.05 * i,
        }
        for i in range(6)
    ]
    scores_path.write_text(json.dumps({"messages": messages}), encoding="utf-8")

    out_png = tmp_path / "roc_single.png"
    result_path = plot_roc_comparison(scores_path, out_png, dpi=150)
    assert result_path == out_png
    _verify_png_file(out_png)


def test_plot_gating_tradeoff(tmp_path: Path) -> None:
    """Verify gating tradeoff plot with online frontier and reproduction grouped bars."""
    _create_sample_paired_comparisons_csv(tmp_path / "paired_comparisons.csv")
    _create_sample_panel_b_csv(tmp_path / "panel_b.csv")

    out_png = tmp_path / "gating_tradeoff.png"
    result_path = plot_gating_tradeoff(tmp_path, out_png, dpi=300)

    assert result_path == out_png
    _verify_png_file(out_png)


def test_plot_gating_tradeoff_without_panel_b(tmp_path: Path) -> None:
    """Verify gating tradeoff plot generates even when panel_b.csv is absent."""
    _create_sample_paired_comparisons_csv(tmp_path / "paired_comparisons.csv")

    out_png = tmp_path / "gating_tradeoff_no_b.png"
    result_path = plot_gating_tradeoff(tmp_path, out_png, dpi=150)

    assert result_path == out_png
    _verify_png_file(out_png)


def test_plot_infection_cascade_no_episodes(tmp_path: Path) -> None:
    """Verify infection cascade placeholder when no infected episodes are found."""
    empty_results = tmp_path / "empty_results"
    empty_results.mkdir()
    out_png = tmp_path / "infection_cascade_empty.png"

    result_path = plot_infection_cascade(empty_results, out_png, dpi=300)
    assert result_path == out_png
    _verify_png_file(out_png)


def test_plot_infection_cascade_with_episodes(tmp_path: Path) -> None:
    """Verify infection cascade diagram when infected episodes exist."""
    results_dir = tmp_path / "campaign"
    _create_sample_episode(results_dir, "ep-101", arm="A1")
    _create_sample_episode(results_dir, "ep-102", arm="A1")

    out_png = tmp_path / "infection_cascade.png"
    result_path = plot_infection_cascade(results_dir, out_png, dpi=300)

    assert result_path == out_png
    _verify_png_file(out_png)


def test_generate_all_figures_full_pipeline(tmp_path: Path) -> None:
    """Integration test verifying generate_all_figures creates all five figures."""
    results_dir = tmp_path / "campaign"
    output_dir = results_dir / "analysis"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    _create_sample_panel_a_csv(output_dir / "panel_a.csv")
    _create_sample_panel_b_csv(output_dir / "panel_b.csv")
    _create_sample_kinetics_csv(output_dir / "kinetics_a1.csv")
    _create_sample_paired_comparisons_csv(output_dir / "paired_comparisons.csv")
    _create_sample_scores_json(results_dir / "scores.json")
    _create_sample_episode(results_dir, "ep-sample", arm="A1")

    figures = generate_all_figures(results_dir=results_dir, output_dir=output_dir, dpi=150)

    expected_keys = {
        "central",
        "kinetics",
        "roc_comparison",
        "gating_tradeoff",
        "infection_cascade",
    }
    assert set(figures.keys()) == expected_keys

    for _key, path in figures.items():
        _verify_png_file(path)


def test_main_cli(tmp_path: Path) -> None:
    """Verify main function CLI interface returns 0 and generates figures."""
    results_dir = tmp_path / "campaign"
    output_dir = results_dir / "analysis"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    _create_sample_scores_json(results_dir / "scores.json")
    _create_sample_paired_comparisons_csv(output_dir / "paired_comparisons.csv")
    _create_sample_panel_a_csv(output_dir / "panel_a.csv")
    _create_sample_panel_b_csv(output_dir / "panel_b.csv")
    _create_sample_kinetics_csv(output_dir / "kinetics_a1.csv")
    _create_sample_episode(results_dir, "ep-cli", arm="A1")

    code = main(
        [
            "--results-dir",
            str(results_dir),
            "--output-dir",
            str(output_dir),
            "--dpi",
            "150",
        ]
    )
    assert code == 0
    assert (output_dir / "roc_comparison.png").is_file()
    assert (output_dir / "gating_tradeoff.png").is_file()
    assert (output_dir / "infection_cascade.png").is_file()
