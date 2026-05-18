"""RQ-019 commander close + status resolver."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.mkm_inter_agent_rq019_status_v1 import resolve_rq019_status
from scripts.record_mkm_inter_agent_rq019_commander_close_v1 import build as build_close


def test_resolve_open_without_artifacts(tmp_path: Path, monkeypatch) -> None:
    import scripts.mkm_inter_agent_rq019_status_v1 as mod

    monkeypatch.setattr(mod, "CLOSE", tmp_path / "close.json")
    monkeypatch.setattr(mod, "SIGNOFF", tmp_path / "signoff.json")
    monkeypatch.setattr(mod, "READINESS", tmp_path / "readiness.json")
    assert resolve_rq019_status() == "OPEN"


def test_resolve_closed_when_close_artifact(tmp_path: Path, monkeypatch) -> None:
    import scripts.mkm_inter_agent_rq019_status_v1 as mod

    close = tmp_path / "close.json"
    close.write_text(json.dumps({"rq_019_closed": True}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(mod, "CLOSE", close)
    monkeypatch.setattr(mod, "SIGNOFF", tmp_path / "signoff.json")
    monkeypatch.setattr(mod, "READINESS", tmp_path / "readiness.json")
    assert resolve_rq019_status() == "CLOSED"


def test_commander_close_requires_counsel_signoff(tmp_path: Path, monkeypatch) -> None:
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps(
            {
                "counsel_signoff": True,
                "counsel_reference": "LC-TEST",
                "rq_019_checklist_item_7_met": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({"closure_allowed": True}, ensure_ascii=False), encoding="utf-8")
    import scripts.record_mkm_inter_agent_rq019_commander_close_v1 as close_mod

    monkeypatch.setattr(close_mod, "SIGNOFF", signoff)
    monkeypatch.setattr(close_mod, "READINESS", readiness)
    doc = build_close(counsel_reference="LC-TEST")
    assert doc["rq_019_closed"] is True
    assert doc["rq_019_status"] == "CLOSED"


def test_commander_close_rejects_reference_mismatch(tmp_path: Path, monkeypatch) -> None:
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps({"counsel_signoff": True, "counsel_reference": "LC-A"}, ensure_ascii=False),
        encoding="utf-8",
    )
    import scripts.record_mkm_inter_agent_rq019_commander_close_v1 as close_mod

    monkeypatch.setattr(close_mod, "SIGNOFF", signoff)
    monkeypatch.setattr(close_mod, "READINESS", tmp_path / "readiness.json")
    with pytest.raises(ValueError, match="mismatch"):
        build_close(counsel_reference="LC-B")
