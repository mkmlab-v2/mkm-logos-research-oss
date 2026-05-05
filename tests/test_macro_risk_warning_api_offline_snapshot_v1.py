from __future__ import annotations

from scripts.build_macro_risk_warning_api_offline_snapshot_v1 import build_snapshot


def test_offline_snapshot_structure() -> None:
    doc = build_snapshot(asset_scope="BTC-USD", horizon="24h", include_evidence_ref=False)
    assert "decision_state" in doc
    assert "risk_warning_level" in doc
    assert "recommended_operator_posture" in doc
