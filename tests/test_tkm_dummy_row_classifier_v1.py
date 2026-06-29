"""Dummy row classifier tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dummy_clinic_capture_fixture() -> None:
    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_clinic_capture

    fixture = json.loads(
        (ROOT / "tests/fixtures/clinic_constitution_mvp_capture_disagreement_v1.example.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert is_dummy_clinic_capture(fixture) is False
    fixture["meta"] = {"dummy_autofill": True}
    assert is_dummy_clinic_capture(fixture) is True


def test_dummy_encounter_sequence() -> None:
    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_encounter_sequence

    row = {"encounter": {"sequence_id": "SEQ-DUMMY-AUTO-01"}, "turns": []}
    assert is_dummy_encounter_sequence(row) is True
