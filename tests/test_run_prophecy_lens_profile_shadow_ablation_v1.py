"""Tier-2 lens profile shadow ablation smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_shadow_ablation_schema_and_arms() -> None:
    out = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_prophecy_lens_profile_shadow_ablation_v1.py")],
            cwd=str(ROOT),
            check=False,
        )
        assert proc.returncode == 0, "shadow ablation script must exit 0"

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_lens_profile_shadow_ablation_v1"
    assert doc.get("research_only") is True
    assert doc.get("send_gate") == "HOLD"
    arms = doc.get("arms") or {}
    for key in ("A", "B", "C", "D", "E"):
        assert key in arms, f"missing arm {key}"
    assert arms["A"]["metrics"]["strategy_id"] == "science+sasang"
    assert "science+logos_by_mode" in arms["D"]
    assert arms["E"].get("returns_pct") is not None


def test_triple_blend_helper_monotonic_signs() -> None:
    from scripts.run_prophecy_lens_profile_shadow_ablation_v1 import _simulate_triple_blend

    rows = [
        {
            "eval_date": "2026-06-01",
            "instrument": "kospi",
            "actual_direction": "bull",
            "daily_return": 0.02,
        },
        {
            "eval_date": "2026-06-02",
            "instrument": "kospi",
            "actual_direction": "bear",
            "daily_return": -0.01,
        },
    ]
    out = _simulate_triple_blend(
        rows=rows,
        btc_prior={},
        myeongni_map={"2026-06-01": 1, "2026-06-02": -1},
        sasang_map={"2026-06-01": 1, "2026-06-02": -1},
        science_sign_map={"2026-06-01": 1, "2026-06-02": -1},
        science_score_map={"2026-06-01": 0.8, "2026-06-02": -0.8},
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert out["strategy_id"] == "science+sasang+myeongni"
    assert out["metrics"]["n_active_days"] == 2
