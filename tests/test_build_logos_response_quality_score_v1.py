"""Tests for build_logos_response_quality_score_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_BUILDER = ROOT / "scripts" / "build_logos_response_retry_inputs_v1.py"
RETRY = ROOT / "scripts" / "run_logos_response_retry_pipeline_v1.py"
SCORER = ROOT / "scripts" / "build_logos_response_quality_score_v1.py"


def test_quality_score_generated_after_retry_selection(tmp_path: Path) -> None:
    mkm_src = ROOT / "docs" / "final" / "artifacts" / "mkm_logos_response_v2_latest.json"
    raw = tmp_path / "raw.txt"
    fallback = tmp_path / "retry.txt"
    selected = tmp_path / "selected.json"
    brief = tmp_path / "brief.md"
    report = tmp_path / "report.json"
    quality = tmp_path / "quality.json"

    r1 = subprocess.run(
        [
            sys.executable,
            str(INPUT_BUILDER),
            "--mkm-json",
            str(mkm_src),
            "--output-raw",
            str(raw),
            "--output-retry",
            str(fallback),
            "--raw-format",
            "fenced",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0, r1.stderr

    r2 = subprocess.run(
        [
            sys.executable,
            str(RETRY),
            "-i",
            str(raw),
            "--retry-input",
            str(fallback),
            "--output-json",
            str(selected),
            "--output-md",
            str(brief),
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stderr

    r3 = subprocess.run(
        [
            sys.executable,
            str(SCORER),
            "--selected-json",
            str(selected),
            "--retry-report-json",
            str(report),
            "--brief-md",
            str(brief),
            "--output-json",
            str(quality),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r3.returncode == 0, r3.stderr
    q = json.loads(quality.read_text(encoding="utf-8"))
    assert q["schema"] == "logos_response_quality_score_v1"
    assert isinstance(q["scores"]["overall"], (int, float))
