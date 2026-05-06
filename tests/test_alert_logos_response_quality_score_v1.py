"""Tests for alert_logos_response_quality_score_v1 script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_logos_response_quality_score_v1.py"


def _write_score(path: Path, overall: float, grade: str) -> None:
    payload = {
        "schema": "logos_response_quality_score_v1",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "scores": {"overall": overall},
        "grade": grade,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_alert_needed_when_overall_below_threshold(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    out = tmp_path / "alert.json"
    _write_score(score, overall=7.2, grade="B")
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--score-json",
            str(score),
            "--output-json",
            str(out),
            "--overall-min",
            "8.0",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["alert_needed"] is True
    assert doc["dispatch_result"] in {"dry_run", "no_webhook_configured"}


def test_no_alert_when_overall_meets_threshold(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    out = tmp_path / "alert.json"
    _write_score(score, overall=9.1, grade="A")
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--score-json",
            str(score),
            "--output-json",
            str(out),
            "--overall-min",
            "8.0",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["alert_needed"] is False
    assert doc["dispatch_result"] == "not_needed"
