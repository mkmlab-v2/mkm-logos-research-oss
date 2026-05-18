"""Counsel submission and manifest smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_mkm_inter_agent_counsel_export_manifest_v1 import build as build_manifest
from scripts.build_mkm_inter_agent_rq019_closure_readiness_v1 import build as build_readiness
from scripts.record_mkm_inter_agent_commander_legal_submission_v1 import build as build_submission


def test_submission_not_counsel_signoff(tmp_path: Path, monkeypatch) -> None:
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps({"technical_closure_ready": True, "checklist": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    import scripts.record_mkm_inter_agent_commander_legal_submission_v1 as sub_mod

    monkeypatch.setattr(sub_mod, "HANDOFF", handoff)
    doc = build_submission()
    assert doc["commander_authorized_legal_submission"] is True
    assert doc["is_counsel_signoff"] is False
    assert doc["legal_review_status"] == "SUBMITTED_TO_COUNSEL"


def test_manifest_lists_files_when_handoff_exists() -> None:
    from scripts.build_mkm_inter_agent_legal_handoff_pack_v1 import DEFAULT_OUT as HANDOFF

    if not HANDOFF.is_file():
        return
    doc = build_manifest()
    assert doc["file_count"] >= 5


def test_closure_readiness_blocked_without_counsel(tmp_path: Path, monkeypatch) -> None:
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "technical_closure_ready": True,
                "checklist": [{"id": 7, "item": "Legal sign-off", "met": False}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    submission = tmp_path / "submission.json"
    submission.write_text(
        json.dumps({"legal_review_status": "SUBMITTED_TO_COUNSEL"}, ensure_ascii=False),
        encoding="utf-8",
    )
    import scripts.build_mkm_inter_agent_rq019_closure_readiness_v1 as readiness_mod

    monkeypatch.setattr(readiness_mod, "HANDOFF", handoff)
    monkeypatch.setattr(readiness_mod, "SIGNOFF", tmp_path / "missing_signoff.json")
    monkeypatch.setattr(readiness_mod, "SUBMISSION", submission)
    monkeypatch.setattr(readiness_mod, "MANIFEST", tmp_path / "manifest.json")
    import scripts.mkm_inter_agent_rq019_status_v1 as status_mod

    monkeypatch.setattr(status_mod, "CLOSE", tmp_path / "missing_close.json")
    monkeypatch.setattr(status_mod, "SIGNOFF", tmp_path / "missing_signoff.json")
    monkeypatch.setattr(status_mod, "READINESS", tmp_path / "missing_readiness.json")

    doc = build_readiness()
    assert doc["closure_allowed"] is False
    assert "legal_signoff_checklist_item_7" in doc["blockers"]


def test_closure_readiness_allowed_with_counsel_signoff(tmp_path: Path, monkeypatch) -> None:
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "technical_closure_ready": True,
                "legal_review_status": "COUNSEL_SIGNED",
                "checklist": [{"id": 7, "item": "Legal sign-off", "met": True}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps(
            {
                "counsel_signoff": True,
                "legal_review_status": "COUNSEL_SIGNED",
                "rq_019_checklist_item_7_met": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    submission = tmp_path / "submission.json"
    submission.write_text(
        json.dumps({"legal_review_status": "SUBMITTED_TO_COUNSEL"}, ensure_ascii=False),
        encoding="utf-8",
    )
    import scripts.build_mkm_inter_agent_rq019_closure_readiness_v1 as readiness_mod

    monkeypatch.setattr(readiness_mod, "HANDOFF", handoff)
    monkeypatch.setattr(readiness_mod, "SIGNOFF", signoff)
    monkeypatch.setattr(readiness_mod, "SUBMISSION", submission)
    monkeypatch.setattr(readiness_mod, "MANIFEST", tmp_path / "manifest.json")
    import scripts.mkm_inter_agent_rq019_status_v1 as status_mod

    monkeypatch.setattr(status_mod, "CLOSE", tmp_path / "missing_close.json")

    doc = build_readiness()
    assert doc["closure_allowed"] is True
    assert doc["legal_review_status"] == "COUNSEL_SIGNED"
