"""pytest: 8-channel clinical weight contract SSOT."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/clinician_ijeoma_eight_channel_weight_contract_v1.json"


def test_eight_channel_contract_shape() -> None:
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "clinician_ijeoma_eight_channel_weight_contract_v1"
    assert doc["decision_authority"] == "human_only"
    assert doc["send_gate"] == "HOLD"
    channels = doc["channels"]
    assert len(channels) == 8
    ids = [c["channel_id"] for c in channels]
    assert len(set(ids)) == 8
    assert doc["synthesis_order"] == ids
    logos = next(c for c in channels if c["channel_id"] == "ch08_logos_non_gating")
    assert logos.get("non_gating") is True
    assert logos["clinical_weight_max"] <= 0.15
    geum = next(c for c in channels if c["channel_id"] == "ch03_geumhwagyoyeok")
    assert geum["clinical_weight_max"] <= 0.2
