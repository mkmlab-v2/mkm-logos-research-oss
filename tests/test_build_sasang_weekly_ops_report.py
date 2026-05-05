from __future__ import annotations

import json
from pathlib import Path

from scripts import build_sasang_weekly_ops_report as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_weekly_ops_report(tmp_path: Path, monkeypatch) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    _write(
        art / "sasang_commercialization_readiness_packet_latest.json",
        {"decision": "READY", "go_no_go": {"go": True, "warnings": ["strict_shadow_evidence_only"], "blockers": []}},
    )
    _write(art / "sasang_ready_drift_check_latest.json", {"status": "STABLE_READY", "drift_detected": False})
    _write(art / "sasang_ready_rollback_drill_latest.json", {"mode": "DRY_RUN"})
    _write(art / "sasang_commercialization_status_chain_latest.json", {"all_exit_zero": True})
    _write(
        art / "sasang_supplemental_insight_score_latest.json",
        {"non_gating_policy": True, "supplemental_score": {"value": 0.96, "band": "HIGH"}},
    )

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "ART", art)
    monkeypatch.setattr(mod, "READINESS", art / "sasang_commercialization_readiness_packet_latest.json")
    monkeypatch.setattr(mod, "DRIFT", art / "sasang_ready_drift_check_latest.json")
    monkeypatch.setattr(mod, "ROLLBACK", art / "sasang_ready_rollback_drill_latest.json")
    monkeypatch.setattr(mod, "STATUS_CHAIN", art / "sasang_commercialization_status_chain_latest.json")
    monkeypatch.setattr(mod, "SUPPLEMENTAL", art / "sasang_supplemental_insight_score_latest.json")
    monkeypatch.setattr(mod, "OUT_LATEST", art / "sasang_weekly_ops_report_latest.json")

    assert mod.main() == 0
    doc = json.loads((art / "sasang_weekly_ops_report_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_weekly_ops_report_v1"
    assert doc["headline"]["go"] is True
    assert doc["supplemental_insights"]["score_band"] == "HIGH"
