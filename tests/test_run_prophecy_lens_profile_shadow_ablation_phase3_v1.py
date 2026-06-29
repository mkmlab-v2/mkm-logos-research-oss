"""Phase-3 shadow ablation smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_phase3_schema() -> None:
    out = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_prophecy_lens_profile_shadow_ablation_phase3_v1.py")],
            cwd=str(ROOT),
            check=False,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_lens_profile_shadow_ablation_phase3_v1"
    assert doc.get("myeongni_sasang_lane", {}).get("metrics")
    assert doc.get("fabba_delta_arms", {}).get("pooled_test_hr")
