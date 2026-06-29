"""Sasang vs myeongni lens separation guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEPARATION = ROOT / "reports/tkm_myeongni_sasang_lens_separation_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"


def test_separation_report_ok() -> None:
    if not SEPARATION.is_file():
        pytest.skip("separation report missing")
    doc = json.loads(SEPARATION.read_text(encoding="utf-8-sig"))
    assert doc.get("separation_ok") is True
    assert int(doc.get("with_sidecar_count") or 0) >= 1


def test_fixture_sidecar_non_gating() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    sidecar = doc.get("l5_myeongni_ref")
    if sidecar is None:
        pytest.skip("fixture sidecar not yet patched")
    assert sidecar.get("non_gating") is True
    assert sidecar.get("sasang_lens_separation_ok") is True
    assert "constitution" not in sidecar


def test_sidecar_validator_module() -> None:
    from scripts.tkm_encounter_sequence_myeongni_sidecar_v1 import (
        attach_sidecar,
        validate_sasang_lens_separation,
    )

    doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    patched = attach_sidecar(doc, myeongni_report_ref="reports/myeongni_physician_gold_stub_v1_latest.json")
    assert validate_sasang_lens_separation(patched) == []
