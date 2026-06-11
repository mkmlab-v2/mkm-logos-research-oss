"""Tests for contributor JSONL validator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/compression/examples/compression_contributor_example_v1.jsonl"
SCRIPT = ROOT / "scripts/validate_compression_contributor_jsonl_v1.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_example_passes_validation(tmp_path: Path) -> None:
    out = tmp_path / "validate.json"
    proc = _run("--jsonl", str(EXAMPLE), "--out-json", str(out), "--min-rows", "10")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["validation_ok"] is True
    assert doc["row_count"] >= 10
    assert doc["auto_track_a_promotion_allowed"] is False


def test_customer_provided_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    row = json.loads(EXAMPLE.read_text(encoding="utf-8").splitlines()[0])
    row["customer_provided"] = True
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = _run("--jsonl", str(bad), "--min-rows", "1")
    assert proc.returncode != 0


def test_forbidden_label_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    row = json.loads(EXAMPLE.read_text(encoding="utf-8").splitlines()[0])
    row["labels"] = list(row["labels"]) + ["operator_panel"]
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = _run("--jsonl", str(bad), "--min-rows", "1")
    assert proc.returncode != 0
