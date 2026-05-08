"""Tests for run_logos_response_retry_pipeline_v1 orchestrator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_response_retry_pipeline_v1.py"
VALID = ROOT / "tests" / "fixtures" / "logos_response_v1_valid_min.json"
INVALID = ROOT / "tests" / "fixtures" / "logos_response_v1_invalid_banned.json"


def test_retry_selects_second_candidate_when_first_fails(tmp_path: Path) -> None:
    out_json = tmp_path / "selected.json"
    out_md = tmp_path / "selected.md"
    report = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "-i",
            str(INVALID),
            "--retry-input",
            str(VALID),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    selected = json.loads(out_json.read_text(encoding="utf-8"))
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert selected["schema"] == "logos_response_v1"
    assert rep["selected"] is True
    assert rep["attempts"][0]["status"] in {"banned_fail", "schema_fail"}
    assert rep["attempts"][-1]["status"] == "ok"


def test_retry_returns_nonzero_when_all_candidates_fail(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "-i",
            str(INVALID),
            "--report-json",
            str(report),
            "--max-attempts",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["selected"] is False
