"""patch_patient_care_bundle_encounter_sequence_ref_v1 — provenance pointer."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.patch_patient_care_bundle_encounter_sequence_ref_v1 import patch_bundle

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "docs/final/schemas/patient_care_bundle_v1.minimal.example.json"


def test_patch_adds_sequence_pointer() -> None:
    bundle = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    patched = patch_bundle(
        bundle,
        encounter_ref="ENC-DEMO-01",
        encounter_sequence_id="SEQ-2026-0618-01",
        encounter_sequence_ledger_ref="data/clinic/encounter_sequence_v1.sample.jsonl",
    )
    prov = patched.get("provenance") or {}
    assert prov.get("encounter_sequence_id") == "SEQ-2026-0618-01"
    assert prov.get("encounter_ref") == "ENC-DEMO-01"
    assert "encounter_sequence_linked_utc" in prov
