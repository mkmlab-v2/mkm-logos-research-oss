"""Multi-turn encounter_sequence smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/patient_intake_multiturn_v1.example.json"


def test_multiturn_build_three_turns() -> None:
    from scripts.build_encounter_sequence_from_intake_v1 import build_from_intake

    intake_doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    doc = build_from_intake(intake_doc, sequence_id="SEQ-TEST-MULTI")
    summary = doc.get("sequence_summary") or {}
    assert int(summary.get("turn_count") or 0) == 3
    confs = summary.get("confidence_trajectory") or []
    assert len(confs) == 3
    assert confs[-1] > confs[0]


def test_physician_gold_not_dummy() -> None:
    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_clinic_capture

    cap = json.loads(
        (ROOT / "tests/fixtures/clinic_constitution_mvp_capture_physician_gold_v1.example.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert is_dummy_clinic_capture(cap) is False
