"""encounter_sequence_ledger_v1 — validate + append."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.encounter_sequence_ledger_v1 import (
    append_encounter_sequence_line,
    validate_encounter_sequence_record,
    validate_jsonl_file,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
SAMPLE = ROOT / "data/clinic/encounter_sequence_v1.sample.jsonl"


def test_fixture_validates() -> None:
    record = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    assert validate_encounter_sequence_record(record) == []


def test_sample_jsonl_validates() -> None:
    assert validate_jsonl_file(SAMPLE) >= 1


def test_append_rejects_bad_domain(tmp_path: Path) -> None:
    bad = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    bad["domain_lane"] = "tcm_clinical"
    with pytest.raises(ValueError, match="domain_lane"):
        append_encounter_sequence_line(tmp_path, bad)


def test_append_writes_daily_file(tmp_path: Path) -> None:
    record = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    record["encounter"] = {
        "ref_token": "ENC-TEST-SEQ-01",
        "sequence_id": "SEQ-TEST-01",
    }
    out = append_encounter_sequence_line(tmp_path, record)
    assert out.exists()
    assert out.name.startswith("encounter_sequence_v1_")
    assert validate_jsonl_file(out) == 1
