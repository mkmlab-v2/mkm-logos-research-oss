from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
XREF = _ROOT / "reports/shadow_canon_gematria_xref_map_v1_latest.json"
AUDIT = _ROOT / "reports/shadow_cross_lane_gematria_audit_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/shadow_cross_lane_gematria_gate_v1_latest.json"
BRIDGE = _ROOT / "reports/shadow_appendix_id_bridge_v1_latest.json"


def test_xref_resolves_shadow_samples() -> None:
    if not XREF.is_file():
        pytest.skip("xref not built")
    doc = json.loads(XREF.read_text(encoding="utf-8-sig"))
    sm = doc.get("summary") or {}
    assert int(sm.get("resolved_shadow_samples") or 0) >= 9
    assert int(sm.get("links_with_samples") or 0) >= 9
    for link in doc.get("links") or []:
        assert len(link.get("shadow_gematria_samples") or []) >= 1


def test_cross_lane_audit_and_gate() -> None:
    if not AUDIT.is_file():
        pytest.skip("audit not built")
    audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
    assert audit.get("schema") == "shadow_cross_lane_gematria_audit_v1"
    assert audit.get("audit_only") is True
    assert audit.get("send_gate") == "HOLD"
    assert int((audit.get("summary") or {}).get("pilot_verses") or 0) >= 9
    if GATE.is_file():
        gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
        assert gate.get("gate_ok") is True
    if BRIDGE.is_file():
        bridge = json.loads(BRIDGE.read_text(encoding="utf-8-sig"))
        sm = bridge.get("summary") or {}
        assert int(sm.get("dss_enriched_appendix_hits") or 0) >= 130
