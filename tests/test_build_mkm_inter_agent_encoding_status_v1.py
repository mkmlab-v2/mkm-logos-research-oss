"""build_mkm_inter_agent_encoding_status_v1 contract smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_mkm_inter_agent_encoding_status_v1 import build_status

ROOT = Path(__file__).resolve().parents[1]


def test_build_status_schema_and_milestones():
    doc = build_status(run_pytest=False)
    assert doc.get("schema") == "mkm_inter_agent_encoding_status_v1"
    assert "milestones" in doc
    for key in ("m1_v2_phase2_packet_only_expand", "m2_wire_profile_v0", "m3_human_decoder_public_copy"):
        assert key in doc["milestones"]
    m2 = doc["milestones"]["m2_wire_profile_v0"]
    assert m2.get("status") == "pass"
    wire = ROOT / "docs" / "final" / "artifacts" / "mkm_inter_agent_wire_profile_v0.json"
    assert wire.is_file()
    payload = json.loads(wire.read_text(encoding="utf-8"))
    assert payload.get("schema") == "mkm_inter_agent_wire_profile_v0"
