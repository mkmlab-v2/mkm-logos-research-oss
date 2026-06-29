"""TKM encounter_sequence P45 curated human-review milestone gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p45_gate_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p45_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p45 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p45_status") == "curated_human_review_milestone_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_curated_review_milestone() -> None:
    if not MILESTONE.is_file():
        pytest.skip("curated review milestone missing")
    doc = json.loads(MILESTONE.read_text(encoding="utf-8-sig"))
    assert doc.get("milestone_ok") is True
    assert doc.get("milestone_threshold_met") is True
    assert doc.get("human_gate_ack_ok") is True
    counts = doc.get("curated_review_counts") if isinstance(doc.get("curated_review_counts"), dict) else {}
    assert int(counts.get("reviewed") or 0) >= int(doc.get("milestone_reviewed_min") or 6)
    assert ARTIFACT.is_file()


def test_weekly_milestone_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.1.0", "3.2.0", "3.3.0", "3.4.0")
    cm = doc.get("curated_review_milestone_kpi")
    assert isinstance(cm, dict)
    assert cm.get("curated_review_milestone_headline_ok") is True
