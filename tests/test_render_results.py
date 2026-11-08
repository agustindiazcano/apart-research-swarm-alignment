import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_results.py"


def get_renderer_module() -> Any:
    spec = importlib.util.spec_from_file_location("render_results", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_results"] = module
    spec.loader.exec_module(module)
    return module


def test_table_rendering_exact_markdown(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    # Fixture data: metrics table
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "summary.csv"
    csv_content = "metric,value\naccuracy,0.95\nloss,0.05\n"
    csv_file.write_text(csv_content, encoding="utf-8")

    source_bytes = csv_content.encode("utf-8")
    expected_hash = hashlib.sha256(source_bytes).hexdigest()

    doc_file = tmp_path / "README.md"
    initial_content = (
        "# Overview\n\n"
        "<!-- RESULTS:BEGIN summary -->\n"
        "placeholder\n"
        "<!-- RESULTS:END summary -->\n"
    )
    doc_file.write_text(initial_content, encoding="utf-8")

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "summary",
                "file": "README.md",
                "source": "results/summary.csv",
                "kind": "table",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    expected_table = (
        "| metric | value |\n"
        "| --- | --- |\n"
        "| accuracy | 0.95 |\n"
        "| loss | 0.05 |\n\n"
        f"Source: `results/summary.csv` (SHA-256 `{expected_hash}`)."
    )
    expected_doc = (
        "# Overview\n\n"
        "<!-- RESULTS:BEGIN summary -->\n"
        f"{expected_table}\n"
        "<!-- RESULTS:END summary -->\n"
    )
    assert doc_file.read_text(encoding="utf-8") == expected_doc

    # Empty CSV (header only) check
    empty_csv_file = results_dir / "empty.csv"
    empty_csv_content = "col1,col2\n"
    empty_csv_file.write_text(empty_csv_content, encoding="utf-8")
    empty_hash = hashlib.sha256(empty_csv_content.encode("utf-8")).hexdigest()

    manifest_data["blocks"].append(
        {
            "name": "empty_block",
            "file": "README.md",
            "source": "results/empty.csv",
            "kind": "table",
        }
    )
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    doc_with_empty = (
        expected_doc
        + "\n<!-- RESULTS:BEGIN empty_block -->\nold\n<!-- RESULTS:END empty_block -->\n"
    )
    doc_file.write_text(doc_with_empty, encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    expected_empty_table = (
        "| col1 | col2 |\n"
        "| --- | --- |\n\n"
        f"Source: `results/empty.csv` (SHA-256 `{empty_hash}`)."
    )
    assert f"<!-- RESULTS:BEGIN empty_block -->\n{expected_empty_table}\n<!-- RESULTS:END empty_block -->" in doc_file.read_text(encoding="utf-8")


def test_columns_selection_and_ordering(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "wide.csv"
    csv_content = "c1,c2,c3\nalpha,beta,gamma\n10,20,30\n"
    csv_file.write_text(csv_content, encoding="utf-8")

    source_bytes = csv_content.encode("utf-8")
    expected_hash = hashlib.sha256(source_bytes).hexdigest()

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "<!-- RESULTS:BEGIN filtered -->\nold\n<!-- RESULTS:END filtered -->\n",
        encoding="utf-8",
    )

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "filtered",
                "file": "README.md",
                "source": "results/wide.csv",
                "kind": "table",
                "columns": ["c3", "c1"],
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    expected_table = (
        "| c3 | c1 |\n"
        "| --- | --- |\n"
        "| gamma | alpha |\n"
        "| 30 | 10 |\n\n"
        f"Source: `results/wide.csv` (SHA-256 `{expected_hash}`)."
    )
    expected_doc = (
        "<!-- RESULTS:BEGIN filtered -->\n"
        f"{expected_table}\n"
        "<!-- RESULTS:END filtered -->\n"
    )
    assert doc_file.read_text(encoding="utf-8") == expected_doc


def test_value_rendering_nested_key_and_missing_key(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_file = results_dir / "stats.json"
    stats_data = {"outer": {"inner": {"target_metric": 42}}}
    json_content = json.dumps(stats_data)
    json_file.write_text(json_content, encoding="utf-8")

    expected_hash = hashlib.sha256(json_content.encode("utf-8")).hexdigest()
    expected_short_hash = expected_hash[:12]

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "<!-- RESULTS:BEGIN metric -->\nold\n<!-- RESULTS:END metric -->\n",
        encoding="utf-8",
    )

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "metric",
                "file": "README.md",
                "source": "results/stats.json",
                "kind": "value",
                "key": "outer.inner.target_metric",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    expected_line = f"42 (source: results/stats.json, SHA-256 {expected_short_hash})"
    expected_doc = (
        "<!-- RESULTS:BEGIN metric -->\n"
        f"{expected_line}\n"
        "<!-- RESULTS:END metric -->\n"
    )
    assert doc_file.read_text(encoding="utf-8") == expected_doc

    # Missing key error test
    manifest_data["blocks"][0]["key"] = "outer.inner.missing_key"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    before_content = doc_file.read_text(encoding="utf-8")
    exit_code_missing_key = renderer.main(["--root", str(tmp_path)])
    assert exit_code_missing_key == 2
    assert doc_file.read_text(encoding="utf-8") == before_content


def test_idempotence_and_check_mode(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "data.csv"
    csv_content = "k,v\nx,1\n"
    csv_file.write_text(csv_content, encoding="utf-8")

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "<!-- RESULTS:BEGIN item -->\ninitial\n<!-- RESULTS:END item -->\n",
        encoding="utf-8",
    )

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "item",
                "file": "README.md",
                "source": "results/data.csv",
                "kind": "table",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Before rendering, --check should exit with code 1 (outdated)
    exit_check_before = renderer.main(["--root", str(tmp_path), "--check"])
    assert exit_check_before == 1

    # First render
    exit_render_1 = renderer.main(["--root", str(tmp_path)])
    assert exit_render_1 == 0
    content_after_first = doc_file.read_text(encoding="utf-8")

    # After rendering, --check should exit with code 0 (up to date)
    exit_check_after = renderer.main(["--root", str(tmp_path), "--check"])
    assert exit_check_after == 0

    # Second render should be idempotent and change nothing
    exit_render_2 = renderer.main(["--root", str(tmp_path)])
    assert exit_render_2 == 0
    content_after_second = doc_file.read_text(encoding="utf-8")
    assert content_after_second == content_after_first


def test_missing_source_file(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    doc_file = tmp_path / "README.md"
    initial_content = (
        "<!-- RESULTS:BEGIN missing -->\ninitial text\n<!-- RESULTS:END missing -->\n"
    )
    doc_file.write_text(initial_content, encoding="utf-8")

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "missing",
                "file": "README.md",
                "source": "results/absent.csv",
                "kind": "table",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # In --check mode, missing source returns 1
    check_exit = renderer.main(["--root", str(tmp_path), "--check"])
    assert check_exit == 1

    # In normal mode, missing source updates block to TODO and returns 2
    render_exit = renderer.main(["--root", str(tmp_path)])
    assert render_exit == 2

    expected_doc = (
        "<!-- RESULTS:BEGIN missing -->\n"
        "TODO(result): source file missing: results/absent.csv\n"
        "<!-- RESULTS:END missing -->\n"
    )
    assert doc_file.read_text(encoding="utf-8") == expected_doc


def test_invalid_markers(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "data.csv"
    csv_file.write_text("a,b\n1,2\n", encoding="utf-8")

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "target",
                "file": "README.md",
                "source": "results/data.csv",
                "kind": "table",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    doc_file = tmp_path / "README.md"

    # Case 1: Missing BEGIN marker
    case1_content = "some text\n<!-- RESULTS:END target -->\n"
    doc_file.write_text(case1_content, encoding="utf-8")
    assert renderer.main(["--root", str(tmp_path)]) == 2
    assert doc_file.read_text(encoding="utf-8") == case1_content

    # Case 2: Missing END marker
    case2_content = "some text\n<!-- RESULTS:BEGIN target -->\n"
    doc_file.write_text(case2_content, encoding="utf-8")
    assert renderer.main(["--root", str(tmp_path)]) == 2
    assert doc_file.read_text(encoding="utf-8") == case2_content

    # Case 3: Duplicated BEGIN marker
    case3_content = (
        "<!-- RESULTS:BEGIN target -->\n"
        "<!-- RESULTS:BEGIN target -->\n"
        "<!-- RESULTS:END target -->\n"
    )
    doc_file.write_text(case3_content, encoding="utf-8")
    assert renderer.main(["--root", str(tmp_path)]) == 2
    assert doc_file.read_text(encoding="utf-8") == case3_content

    # Case 4: Duplicated END marker
    case4_content = (
        "<!-- RESULTS:BEGIN target -->\n"
        "<!-- RESULTS:END target -->\n"
        "<!-- RESULTS:END target -->\n"
    )
    doc_file.write_text(case4_content, encoding="utf-8")
    assert renderer.main(["--root", str(tmp_path)]) == 2
    assert doc_file.read_text(encoding="utf-8") == case4_content

    # Case 5: END marker precedes BEGIN marker
    case5_content = (
        "<!-- RESULTS:END target -->\n"
        "middle\n"
        "<!-- RESULTS:BEGIN target -->\n"
    )
    doc_file.write_text(case5_content, encoding="utf-8")
    assert renderer.main(["--root", str(tmp_path)]) == 2
    assert doc_file.read_text(encoding="utf-8") == case5_content


def test_unlisted_markers_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_file = results_dir / "data.csv"
    csv_file.write_text("metric,val\nm,1\n", encoding="utf-8")
    source_bytes = "metric,val\nm,1\n".encode("utf-8")
    expected_hash = hashlib.sha256(source_bytes).hexdigest()

    doc_file = tmp_path / "README.md"
    initial_content = (
        "<!-- RESULTS:BEGIN listed -->\nold listed\n<!-- RESULTS:END listed -->\n\n"
        "<!-- RESULTS:BEGIN unlisted_item -->\nkeep unchanged\n<!-- RESULTS:END unlisted_item -->\n"
    )
    doc_file.write_text(initial_content, encoding="utf-8")

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "listed",
                "file": "README.md",
                "source": "results/data.csv",
                "kind": "table",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "unlisted_item" in captured.err

    content = doc_file.read_text(encoding="utf-8")
    assert "<!-- RESULTS:BEGIN unlisted_item -->\nkeep unchanged\n<!-- RESULTS:END unlisted_item -->" in content
    assert f"Source: `results/data.csv` (SHA-256 `{expected_hash}`)." in content


def test_crlf_preservation(tmp_path: Path) -> None:
    renderer = get_renderer_module()

    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_file = results_dir / "value.json"
    json_file.write_text('{"score": 99}', encoding="utf-8")

    doc_file = tmp_path / "README.md"
    crlf_bytes = b"# CRLF Doc\r\n\r\n<!-- RESULTS:BEGIN val -->\r\nold\r\n<!-- RESULTS:END val -->\r\n"
    doc_file.write_bytes(crlf_bytes)

    manifest_file = results_dir / "render_manifest.json"
    manifest_data = {
        "blocks": [
            {
                "name": "val",
                "file": "README.md",
                "source": "results/value.json",
                "kind": "value",
                "key": "score",
            }
        ]
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    exit_code = renderer.main(["--root", str(tmp_path)])
    assert exit_code == 0

    updated_bytes = doc_file.read_bytes()
    assert b"\r\n" in updated_bytes
    assert b"\r\r\n" not in updated_bytes

    # Ensure no lone \n exists without preceding \r
    lines_raw = updated_bytes.split(b"\r\n")
    for segment in lines_raw:
        assert b"\n" not in segment
