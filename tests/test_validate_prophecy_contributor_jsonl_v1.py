"""Tests for prophecy contributor JSONL validator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/prophecy/examples/prophecy_contributor_example_v1.jsonl"
SCRIPT = ROOT / "scripts/validate_prophecy_contributor_jsonl_v1.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_example_passes_validation(tmp_path: Path) -> None:
    out = tmp_path / "validate.json"
    proc = _run("--jsonl", str(EXAMPLE), "--out-json", str(out), "--min-rows", "5")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["validation_ok"] is True
    assert doc["row_count"] >= 5
    assert doc.get("resolved_count", 0) >= 3


def test_customer_provided_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    row = json.loads(EXAMPLE.read_text(encoding="utf-8").splitlines()[0])
    row["customer_provided"] = True
    bad.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    proc = _run("--jsonl", str(bad), "--min-rows", "1")
    assert proc.returncode != 0
