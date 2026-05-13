"""Smoke: report_aramaic_insight_cap_threshold_history_v1 appends a history row (tmp jsonl)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep_aramaic_insight_cap_bucket_thresholds_v1.py"
APPLY = ROOT / "scripts" / "apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py"
REPORT = ROOT / "scripts" / "report_aramaic_insight_cap_threshold_history_v1.py"


def test_report_insight_cap_threshold_history_cli_smoke(tmp_path: Path) -> None:
    sweep_out = tmp_path / "sweep.json"
    rec_out = tmp_path / "rec.json"
    hist = tmp_path / "history.jsonl"
    subprocess.run(
        [sys.executable, str(SWEEP), "--output-json", str(sweep_out)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, str(APPLY), "--sweep-json", str(sweep_out), "--output-json", str(rec_out)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(REPORT),
            "--recommended-json",
            str(rec_out),
            "--history-jsonl",
            str(hist),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in hist.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("schema") == "aramaic_insight_cap_bucket_threshold_history_row_v1"
