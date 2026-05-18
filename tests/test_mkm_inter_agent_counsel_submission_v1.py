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


def test_closure_readiness_blocked_without_counsel() -> None:
    doc = build_readiness()
    assert doc["closure_allowed"] is False
    assert "legal_signoff" in str(doc["blockers"][0])
