"""TKM encounter_sequence P17 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p17_gate_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
DISAGREE = ROOT / "tests/fixtures/encounter_sequence_disagreement_v1.example.json"


def test_p17_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p17 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p17_status") == "l0_curated_weekly_ok"


def test_weekly_report() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("weekly_ok") is True


def test_curated_draft_builder_disagreement(tmp_path: Path) -> None:
    from scripts.build_encounter_sequence_curated_learning_draft_v1 import build

    disagree = json.loads(DISAGREE.read_text(encoding="utf-8-sig"))
    path = tmp_path / "disagree.jsonl"
    path.write_text(json.dumps(disagree, ensure_ascii=False) + "\n", encoding="utf-8")
    doc = build(paths=[path])
    assert doc.get("draft_ok") is True
    assert int(doc.get("disagreement_draft_count") or 0) == 1
