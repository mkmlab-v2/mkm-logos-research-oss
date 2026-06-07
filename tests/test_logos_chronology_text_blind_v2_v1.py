"""Smoke tests for text_blind_v2 era eval (B-track; MS baseline unchanged)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "scripts/run_logos_chronology_text_blind_v2_ab_v1.py"
GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"


def test_text_blind_v2_ab_improves_over_v1_baseline() -> None:
    if not GOLD.is_file() or not CHRONO.is_file():
        return
    cp = subprocess.run(
        [sys.executable, str(AB)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = ROOT / "reports/logos_chronology_text_blind_v2_ab_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    v1 = float(doc["compare"]["hit_at_1_strict_v1"])
    v2 = float(doc["compare"]["hit_at_1_strict_v2"])
    assert v2 > v1
    assert v2 >= 0.15
