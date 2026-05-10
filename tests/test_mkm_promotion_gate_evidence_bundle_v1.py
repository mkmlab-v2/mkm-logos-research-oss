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


def test_compression_pilot_report_paths_schema_v1() -> None:
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "artifacts" / "MKM_AI_COMPRESSION_PILOT_REPORT_PATHS_V1.json"
    assert p.is_file(), f"missing {p}"
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("schema") == "mkm_ai_compression_pilot_report_paths_v1"
    assert "paths" in d
    assert "multilens_ultra_active_report" in d["paths"]
