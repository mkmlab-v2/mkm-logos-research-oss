"""Tests for promotion readiness report builder."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_streak_blocker_when_strict_passed_but_streak_low() -> None:
    path = ROOT / "scripts/build_prophecy_promotion_readiness_report_v1.py"
    spec = importlib.util.spec_from_file_location("build_prophecy_promotion_readiness_report_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    doc = mod.build_report(
        gates={
            "strict_passed": True,
            "all_gates_passed": True,
            "auto_promote_ready": False,
            "strict_pass_streak": 1,
            "inputs": {"strict_streak_required": 5},
            "promotion_recommendation": "manual_review_candidate",
        },
        hit={"metrics": {"price_directional_hit_rate": 0.433333, "n_evaluated": 30}},
    )
    assert doc["auto_promote_ready"] is False
    assert any(b["code"] == "STRICT_STREAK_INSUFFICIENT" for b in doc["blockers"])
