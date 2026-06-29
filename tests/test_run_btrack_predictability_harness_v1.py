# @MKM12-METADATA
# Type: Logic
# Purpose: B-track predictability harness smoke (gate + Brier + drift log).

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"
_HARNESS = _ROOT / "scripts" / "run_btrack_predictability_harness_v1.py"
_VALIDATE = _ROOT / "scripts" / "validate_general_prophecy_predictability_input_v1.py"


def test_predictability_gate_rejects_non_binary() -> None:
    bad = {
        "schema": "general_prophecy_registry_v1",
        "research_rail": "B",
        "generated_at_utc": "2026-06-04T00:00:00Z",
        "questions": [
            {
                "schema": "general_prophecy_question_v1",
                "research_rail": "B",
                "question_id": "bad.open.narrative_v1",
                "question_text": "반도체주가 상승할 것인가?",
                "resolution_deadline_utc": "2026-12-31T00:00:00Z",
                "resolution_criteria": "short",
                "outcome_spec": {"kind": "categorical", "categories": ["up", "down"]},
            }
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad_registry.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(_VALIDATE), "-i", str(p), "--stdout-only", "--no-jsonschema"],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    assert r.returncode == 2
    doc = json.loads(r.stdout)
    assert doc.get("gate_pass") is False
    assert doc.get("rejected")


def test_predictability_harness_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(_HARNESS), "--dry-run", "-i", str(_FIXTURE)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout.strip())
    assert doc.get("dry_run") is True
    assert "validate" in doc.get("plan", {})


def test_predictability_harness_on_brier_fixture() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        brier_out = td_path / "brier.json"
        harness_out = td_path / "harness.json"
        drift_log = td_path / "drift.jsonl"
        r = subprocess.run(
            [
                sys.executable,
                str(_HARNESS),
                "-i",
                str(_FIXTURE),
                "--brier-output",
                str(brier_out),
                "--harness-output",
                str(harness_out),
                "--drift-log",
                str(drift_log),
                "--no-jsonschema",
            ],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 0, r.stderr
        assert brier_out.is_file()
        assert harness_out.is_file()
        assert drift_log.is_file()
        harness = json.loads(harness_out.read_text(encoding="utf-8"))
        assert harness.get("harness_pass") is True
        assert harness.get("metrics", {}).get("n_evaluated") == 1
        lines = drift_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        drift = json.loads(lines[0])
        assert drift.get("schema") == "btrack_predictability_brier_drift_v1"
        assert drift.get("mean_brier_score") is not None
