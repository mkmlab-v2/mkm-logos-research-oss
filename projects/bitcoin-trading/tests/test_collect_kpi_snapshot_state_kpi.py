from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "ops"
        / "windows-rehearsal"
        / "collect_kpi_snapshot.py"
    )
    spec = importlib.util.spec_from_file_location("collect_kpi_snapshot", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extract_dual_regime_state_kpi_prefers_trader_state_summary():
    mod = _load_module()
    status = {
        "mkm_singular_core": {
            "last_signal_summary": {
                "risk_assessment": {
                    "dual_regime_context": {"state_id": 5, "state_id_source": "fallback"},
                    "signal_registry_clamped": False,
                }
            }
        }
    }
    trader_state = {
        "last_signal_summary": {
            "risk_assessment": {
                "dual_regime_context": {"state_id": 9, "state_id_source": "risk_assessment.myeongni_state_id"},
                "signal_registry_clamped": True,
                "signal_registry_cap": 0.7,
            }
        }
    }

    out = mod._extract_dual_regime_state_kpi(status, trader_state)
    assert out["state_id"] == 9
    assert out["state_id_source"] == "risk_assessment.myeongni_state_id"
    assert out["state_id_present"] is True
    assert out["signal_registry_clamped"] is True
    assert out["signal_registry_cap"] == 0.7
    assert out["source_count"] == {"risk_assessment.myeongni_state_id": 1}
    assert out["clamp_count"] == 1


def test_extract_dual_regime_state_kpi_defaults_to_none_when_missing():
    mod = _load_module()
    out = mod._extract_dual_regime_state_kpi(status={}, trader_state={})
    assert out["state_id"] is None
    assert out["state_id_source"] == "none"
    assert out["state_id_present"] is False
    assert out["signal_registry_clamped"] is False
    assert out["signal_registry_cap"] is None
    assert out["source_count"] == {"none": 1}
    assert out["clamp_count"] == 0
    assert out["sample_count"] == 1

