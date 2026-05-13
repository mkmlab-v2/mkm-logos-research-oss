"""Smoke: apply_aramaic_insight_cap_bucket_threshold_recommendation_v1 reads sweep and writes recommendation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep_aramaic_insight_cap_bucket_thresholds_v1.py"
APPLY = ROOT / "scripts" / "apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py"


def test_apply_insight_cap_bucket_threshold_recommendation_cli_smoke(tmp_path: Path) -> None:
    sweep_out = tmp_path / "sweep.json"
    rec_out = tmp_path / "rec.json"
    p1 = subprocess.run(
        [sys.executable, str(SWEEP), "--output-json", str(sweep_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p1.returncode == 0, p1.stderr
    p2 = subprocess.run(
        [sys.executable, str(APPLY), "--sweep-json", str(sweep_out), "--output-json", str(rec_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p2.returncode == 0, p2.stderr
    doc = json.loads(rec_out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "aramaic_insight_cap_bucket_threshold_recommendation_v1"
    assert "mid_vol_threshold" in (doc.get("recommended") or {})
