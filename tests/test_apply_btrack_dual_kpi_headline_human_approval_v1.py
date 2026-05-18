"""Tests for KPI-B operational headline human approval apply script."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_script_constants() -> None:
    path = ROOT / "scripts/apply_btrack_dual_kpi_headline_human_approval_v1.py"
    spec = importlib.util.spec_from_file_location("apply_btrack_dual_kpi", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    assert mod.DEFAULT_APPROVAL_OUT.name == "btrack_dual_kpi_headline_human_approval_v1_latest.json"
    assert mod.ARCHIVE_EVAL.name == "prophecy_hit_rate_eval_kpi_a_frozen_archive_v1_latest.json"
    assert mod.SHADOW_EVAL.name == "prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"


def test_policy_json_schema() -> None:
    policy_path = ROOT / "docs/final/artifacts/btrack_dual_kpi_headline_policy_v1.json"
    obj = json.loads(policy_path.read_text(encoding="utf-8"))
    assert obj["schema"] == "btrack_dual_kpi_headline_policy_v1"
    assert obj["live_trading_auto_enable"] is False
    assert obj["track_a_auto_promote"] is False
    assert obj["kpi_b_per_date"]["role"] == "operational_headline_after_human_approval"
