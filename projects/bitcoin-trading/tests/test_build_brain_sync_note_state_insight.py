from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "ops"
        / "windows-rehearsal"
        / "build_brain_sync_note.py"
    )
    spec = importlib.util.spec_from_file_location("build_brain_sync_note", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dual_regime_state_insight_aggregates_sources_and_clamp(tmp_path):
    mod = _load_module()
    mod.KPI_DIR = tmp_path
    day_file = tmp_path / "kpi_snapshot_20260401.jsonl"
    rows = [
        {"dual_regime_state_kpi": {"state_id_source": "none", "state_id_present": False, "signal_registry_clamped": False}},
        {
            "dual_regime_state_kpi": {
                "state_id_source": "risk_assessment.myeongni_state_id",
                "state_id_present": True,
                "signal_registry_clamped": True,
            }
        },
        {
            "dual_regime_state_kpi": {
                "state_id_source": "risk_assessment.myeongni_state_id",
                "state_id_present": True,
                "signal_registry_clamped": False,
            }
        },
    ]
    day_file.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    out = mod._kpi_dual_regime_state_insight(limit=10)
    assert out["available"] is True
    assert out["samples"] == 3
    assert out["state_id_present_count"] == 2
    assert out["clamp_count"] == 1
    assert out["top_source"] == "risk_assessment.myeongni_state_id"
    assert out["source_counts"]["risk_assessment.myeongni_state_id"] == 2


def test_dual_regime_state_insight_handles_missing_history(tmp_path):
    mod = _load_module()
    mod.KPI_DIR = tmp_path
    out = mod._kpi_dual_regime_state_insight(limit=10)
    assert out["available"] is False
    assert out["reason"] == "no_kpi_history"


def test_slack_advisory_summary_reads_top_decisions(tmp_path):
    mod = _load_module()
    report = tmp_path / "slack_advisory_history_latest.json"
    report.write_text(
        json.dumps(
            {
                "window_days": 7,
                "rows_in_window": 9,
                "dual_regime_state_advisory_decision_counts": {"state_clamp_stable": 7, "insufficient_data": 2},
                "auto_hold_override_advisory_decision_counts": {"override_mix_balanced": 9},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    old_path = mod.SLACK_ADVISORY_HISTORY
    mod.SLACK_ADVISORY_HISTORY = report
    try:
        out = mod._slack_advisory_summary()
    finally:
        mod.SLACK_ADVISORY_HISTORY = old_path
    assert out["available"] is True
    assert out["dual_top_decision"] == "state_clamp_stable"
    assert out["override_top_decision"] == "override_mix_balanced"


def test_unknown_ratio_helper():
    mod = _load_module()
    assert mod._unknown_ratio({"unknown": 7}, 10) == 0.7
    assert mod._unknown_ratio({}, 0) is None

