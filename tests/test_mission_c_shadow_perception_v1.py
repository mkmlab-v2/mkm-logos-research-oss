"""Tests for Mission C shadow ops status + passive alerts."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_build_status_observe_posture() -> None:
    mod = _load_module("build_mission_c_shadow_ops_status_v1", "scripts/build_mission_c_shadow_ops_status_v1.py")
    summary = {
        "recipe_id": "mission_c_srcdir_expanded_v1",
        "wf_aggregate": {"mean_test_accuracy": 0.56, "stdev_test_accuracy": 0.1},
        "gates": {
            "strict_passed": True,
            "outcome_class": "pass_candidate",
            "strict_pass_streak": 2,
            "strict_streak_required": 5,
            "auto_promote_ready": False,
        },
    }
    doc = mod.build_status(summary=summary, gates=None, streak_doc=None, briefing_path=Path("nope.md"))
    assert doc["operator_posture"] == "streak_accumulating"
    assert doc["research_only"] is True
    assert doc["telegram_digest_block"]["do_not_auto_promote"] is True


def test_evaluate_alerts_milestone() -> None:
    mod = _load_module("check_mission_c_shadow_passive_alerts_v1", "scripts/check_mission_c_shadow_passive_alerts_v1.py")
    ops = {
        "gates": {
            "strict_passed": True,
            "strict_pass_streak": 5,
            "strict_streak_required": 5,
            "auto_promote_ready": True,
            "outcome_class": "pass_candidate",
        },
        "telegram_digest_block": {"one_liner": "test"},
    }
    alerts = mod.evaluate_alerts(ops)
    assert any(a["alert_id"] == "MISSION_C_STREAK_MILESTONE" for a in alerts)
    assert alerts[0]["notify"] is True


def test_evaluate_alerts_observe_no_notify() -> None:
    mod = _load_module("check_mission_c_shadow_passive_alerts_v1", "scripts/check_mission_c_shadow_passive_alerts_v1.py")
    ops = {
        "gates": {
            "strict_passed": True,
            "strict_pass_streak": 1,
            "strict_streak_required": 5,
            "auto_promote_ready": False,
            "outcome_class": "pass_candidate",
        },
        "telegram_digest_block": {"one_liner": "ok"},
    }
    alerts = mod.evaluate_alerts(ops)
    assert alerts[0]["alert_id"] == "MISSION_C_OBSERVE"
    assert alerts[0]["notify"] is False
