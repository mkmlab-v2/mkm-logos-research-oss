"""Convert clinic capture → encounter_sequence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_disagreement_v1.example.json"


def test_convert_disagreement_capture() -> None:
    from scripts.convert_clinic_capture_to_encounter_sequence_v1 import convert_capture

    capture = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    doc = convert_capture(capture, sequence_id="SEQ-TEST-CONV")
    assert doc["schema"] == "encounter_sequence_v1"
    closure = doc.get("physician_closure") or {}
    agr = closure.get("agreement") or {}
    assert agr.get("ai_physician_match") is False
    assert agr.get("disagreement_code") == "ai_overconfident"
    assert doc.get("curated_learning_pointer", {}).get("disagreement_recorded") is True
    assert isinstance(doc.get("l5_myeongni_ref"), dict)
    assert isinstance(doc.get("l6_logos_ref"), dict)
    assert isinstance(doc.get("l7_conflict_resolver_ref"), dict)
    assert doc["l7_conflict_resolver_ref"].get("final_action_observed") == "physician_authority_preserved"


def test_ingest_idempotent() -> None:
    from scripts.ingest_clinic_capture_to_encounter_sequence_v1 import ingest

    capture = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    first = ingest(capture, append_clinic_ledger=False, sequence_id="SEQ-TEST-IDEM")
    second = ingest(capture, append_clinic_ledger=False, sequence_id="SEQ-TEST-IDEM")
    assert first.get("ok") is True
    assert second.get("already_present") is True
