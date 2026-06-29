"""Dummy autofill bootstrap smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_dummy_autofill_bootstrap() -> None:
    from scripts.bootstrap_tkm_encounter_sequence_dummy_autofill_v1 import autofill

    doc = autofill(min_clinic_captures=5)
    assert doc.get("autofill_ok") is True
    assert int(doc.get("clinic_capture_count") or 0) >= 5
    assert int(doc.get("encounter_sequence_count") or 0) >= 1


def test_dummy_autofill_report() -> None:
    path = ROOT / "reports/tkm_encounter_sequence_dummy_autofill_v1_latest.json"
    if not path.is_file():
        pytest.skip("autofill report missing")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("dummy_autofill") is True
