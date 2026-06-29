"""Clinic MVP disagreement summary builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_clinic_mvp_disagreement_summary_v1 import build_disagreement_summary
from scripts.clinic_constitution_mvp_ledger_v1 import validate_jsonl_file

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data/clinic/clinic_constitution_mvp_v1.sample.jsonl"


def _load_sample_records() -> list[dict]:
    records = []
    for line in SAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def test_sample_two_lines_one_match_one_mismatch() -> None:
    assert validate_jsonl_file(SAMPLE) == 2
    records = _load_sample_records()
    summary = build_disagreement_summary(
        records,
        ledger_files=["data/clinic/clinic_constitution_mvp_v1.sample.jsonl"],
        parse_errors=[],
    )
    assert summary["schema"] == "clinic_mvp_disagreement_summary_v1"
    assert summary["n_lines_valid"] == 2
    assert summary["n_comparable_four_label"] == 1  # line1 ai=uncertain excluded
    assert summary["n_ai_physician_match"] == 1
    assert summary["match_rate"] == 1.0
    assert summary["disagreement_rate"] == 0.0
    assert summary["research_only"] is True
    assert summary["guards"]["not_for_track_a_promotion"] is True


def test_empty_records() -> None:
    summary = build_disagreement_summary([], ledger_files=[], parse_errors=[])
    assert summary["n_lines_valid"] == 0
    assert summary["match_rate"] is None
    assert summary["disagreement_rate"] is None
