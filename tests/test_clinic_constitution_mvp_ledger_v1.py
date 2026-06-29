"""Clinic constitution MVP ledger — validate + append."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.clinic_constitution_mvp_ledger_v1 import (
    append_clinic_capture_line,
    validate_clinic_capture_record,
    validate_jsonl_file,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_v1.example.json"
SAMPLE = ROOT / "data/clinic/clinic_constitution_mvp_v1.sample.jsonl"


def test_fixture_validates() -> None:
    record = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert validate_clinic_capture_record(record) == []


def test_sample_jsonl_validates() -> None:
    assert validate_jsonl_file(SAMPLE) >= 1


def test_append_rejects_missing_boundary(tmp_path: Path) -> None:
    bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bad["boundary_ack"] = False
    with pytest.raises(ValueError, match="boundary_ack"):
        append_clinic_capture_line(tmp_path, bad)


def test_append_writes_daily_file(tmp_path: Path) -> None:
    record = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record["encounter"] = {"ref_token": "ENC-TEST-APPEND-01"}
    out = append_clinic_capture_line(tmp_path, record)
    assert out.exists()
    assert out.name.startswith("clinic_constitution_mvp_v1_")
    assert validate_jsonl_file(out) == 1
