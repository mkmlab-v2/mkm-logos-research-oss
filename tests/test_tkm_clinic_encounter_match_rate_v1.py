"""TKM clinic/encounter match rate unit tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.tkm_clinic_encounter_match_rate_v1 import extract_ai_physician_labels, match_rate

ROOT = Path(__file__).resolve().parents[1]
ENC_FIXTURE = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
CLINIC_FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_physician_gold_v1.example.json"


def test_encounter_fixture_labels() -> None:
    row = json.loads(ENC_FIXTURE.read_text(encoding="utf-8-sig"))
    pair = extract_ai_physician_labels(row)
    assert pair == ("soeum", "soeum")


def test_clinic_fixture_labels() -> None:
    row = json.loads(CLINIC_FIXTURE.read_text(encoding="utf-8-sig"))
    pair = extract_ai_physician_labels(row)
    assert pair == ("soyang", "soeum")


def test_match_rate_on_encounter_fixture() -> None:
    row = json.loads(ENC_FIXTURE.read_text(encoding="utf-8-sig"))
    rate = match_rate([row])
    assert rate == 1.0
