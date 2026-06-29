"""Shadow ablation v2 — 180d/2bps + E_dynamic smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_arm_e_dynamic_simulator_runs() -> None:
    from scripts.run_prophecy_lens_profile_shadow_ablation_v2 import _simulate_arm_e_dynamic

    rows = [
        {"eval_date": "2026-06-01", "daily_return": 0.01, "actual_direction": "bull"},
        {"eval_date": "2026-06-02", "daily_return": -0.005, "actual_direction": "bear"},
        {"eval_date": "2026-06-03", "daily_return": 0.02, "actual_direction": "bull"},
    ]
    out = _simulate_arm_e_dynamic(
        rows=rows,
        science_sign_map={"2026-06-01": 1, "2026-06-02": 1, "2026-06-03": 1},
        science_score_map={"2026-06-01": 0.5, "2026-06-02": 0.5, "2026-06-03": 0.5},
        myeongni_map={},
        sasang_map={"2026-06-01": 1, "2026-06-02": 1, "2026-06-03": 1},
        logos_sign=-1,
        closes={"2026-06-01": 100.0, "2026-06-02": 101.0, "2026-06-03": 100.5},
        veto_map={},
        supplier_map={"2026-06-01": True, "2026-06-02": True, "2026-06-03": True},
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert out["arm_id"] == "E_dynamic"
    assert out["metrics"]["n_days"] == 3


def test_v2_artifact_schema() -> None:
    out = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v2_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_prophecy_lens_profile_shadow_ablation_v2.py")],
            cwd=str(ROOT),
            check=False,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_lens_profile_shadow_ablation_v2"
    assert doc.get("protocol", {}).get("fee_bps") == 2.0
    assert "E_dynamic" in (doc.get("arms") or {})
    assert "walkforward" in doc
