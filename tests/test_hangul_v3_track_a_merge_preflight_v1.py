"""Track A v3 merge preflight — subset guard + gate contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/HANGUL_V3_TRACK_A_MERGE_PREFLIGHT_CONTRACT_V1.json"
GATE = ROOT / "reports/hangul_v3_track_a_merge_preflight_gate_v1_latest.json"
PACKET = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"


def test_contract_forbids_naive_prod_swap():
    assert CONTRACT.is_file()
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    gates = doc.get("gates") or {}
    assert gates.get("production_pointer_swap") is False
    forbidden = " ".join(doc.get("forbidden") or [])
    assert "41676" in forbidden or "v3" in forbidden.lower()


def test_gate_packet_scope_when_present():
    if not GATE.is_file() or not PACKET.is_file():
        return
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    assert gate.get("production_pointer_swap") is False
    scope = packet.get("promotion_scope") or {}
    assert scope.get("production_ssot_swap") is False
    assert scope.get("multilens_active_report_write") is False
    assert packet.get("philosophy_summary", {}).get("v3_is_strict_subset") is True


def test_merge_lib_subset_audit_fixture():
    from scripts.hangul_v3_track_a_merge_lib_v1 import subset_audit

    production = {
        "entries": [
            {"lang": "ko", "normalized_form": "체질", "atom_id": "hangul_curated_v1::체질"},
            {"lang": "ko", "normalized_form": "태양", "atom_id": "hangul_curated_v1::태양"},
        ]
    }
    v3 = {"entries": [{"lang": "ko", "normalized_form": "체질", "atom_id": "hangul_curated_v1::체질"}]}
    audit = subset_audit(production, v3)
    assert audit["v3_is_subset_of_production"] is True
    assert audit["naive_v3_swap_regresses_ko"] is True
    assert audit["prod_only_count"] == 1
