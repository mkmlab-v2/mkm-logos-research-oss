"""Build encounter_sequence from intake fusion input."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/patient_intake_encounter_sequence_v1.example.json"


def test_build_from_intake_l0_triggered() -> None:
    from scripts.build_encounter_sequence_from_intake_v1 import build_from_intake

    intake_doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    doc = build_from_intake(intake_doc, sequence_id="SEQ-TEST-L0")
    assert doc["schema"] == "encounter_sequence_v1"
    assert doc["l0_router_events"]
    assert doc["l0_router_events"][0].get("triggered") is True
    assert "severe_abdominal_pain" in (doc["l0_router_events"][0].get("keyword_hits") or [])


def test_apply_curated_learning_requires_ack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import apply_encounter_sequence_curated_learning_v1 as mod

    draft = {
        "drafts": [
            {
                "sequence_id": "SEQ-TEST",
                "disagreement_code": "ai_overconfident",
            }
        ],
        "draft_ok": True,
        "disagreement_draft_count": 1,
    }
    draft_path = tmp_path / "drafts.json"
    draft_path.write_text(json.dumps(draft), encoding="utf-8")
    ack_path = tmp_path / "ack.json"
    reg_path = tmp_path / "registry.jsonl"
    monkeypatch.setattr(mod, "DRAFTS", draft_path)
    monkeypatch.setattr(mod, "ACK", ack_path)
    monkeypatch.setattr(mod, "REGISTRY", reg_path)

    denied = mod.apply(human_gate_ack=False)
    assert denied.get("applied") is False
    assert denied.get("reason") == "human_gate_ack_required"

    ok_dummy = mod.apply(dummy_auto_fill=True)
    assert ok_dummy.get("applied") is True
    assert ok_dummy.get("dummy_autofill") is True

    ok = mod.apply(human_gate_ack=True)
    assert ok.get("applied") is True
    assert ack_path.is_file()
    assert reg_path.is_file()
