"""Contract smoke for mkm_promotion_gate_evidence_bundle_v1.json SSOT."""

from __future__ import annotations

import json
from pathlib import Path


def test_promotion_gate_evidence_bundle_schema_v1() -> None:
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "artifacts" / "mkm_promotion_gate_evidence_bundle_v1.json"
    assert p.is_file(), f"missing {p}"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("schema") == "mkm_promotion_gate_evidence_bundle_v1"
    assert "gates" in d
    assert d["gates"].get("G12", {}).get("status") == "human_required"
    integ = d.get("track_a_regeneration_integrity") or {}
    assert integ.get("worst_case") in {
        "ok",
        "stale_snapshot_risk",
        "producer_gap",
        "regeneration_optional",
    }
    for gid in ("G4", "G5", "G6"):
        g = d["gates"].get(gid) or {}
        assert g.get("producer_script")
        assert "producer_present" in g
        assert g.get("status") in ("pass", "optional_missing", "stale_snapshot", "producer_gap")


def test_compression_pilot_report_paths_schema_v1() -> None:
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "artifacts" / "MKM_AI_COMPRESSION_PILOT_REPORT_PATHS_V1.json"
    assert p.is_file(), f"missing {p}"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("schema") == "mkm_ai_compression_pilot_report_paths_v1"
    assert "paths" in d
    assert "multilens_ultra_active_report" in d["paths"]
    assert (
        d["paths"].get("vps_bench_one_click_script")
        == "scripts/deploy/linux/run_bench_l1_api_load_vps_fixed_fields.sh"
    )
