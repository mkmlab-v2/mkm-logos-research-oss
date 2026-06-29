"""TKM encounter_sequence P52 NotebookLM export sync gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p52_gate_v1_latest.json"
SYNC = ROOT / "reports/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_manifest_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p52_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p52 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p52_status") == "notebooklm_export_sync_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_notebooklm_export_sync() -> None:
    if not SYNC.is_file():
        pytest.skip("notebooklm export sync missing")
    doc = json.loads(SYNC.read_text(encoding="utf-8-sig"))
    assert doc.get("export_sync_ok") is True
    assert doc.get("cloud_upload_forbidden") is True
    assert doc.get("cloud_upload_attempted") is False
    assert int(doc.get("manifest_files_present_count") or 0) >= 11
    assert ARTIFACT.is_file()
    assert MANIFEST.is_file()


def test_weekly_export_sync_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.8.0", "3.9.0", "4.0.0")
    nes = doc.get("notebooklm_export_sync_kpi")
    assert isinstance(nes, dict)
    assert nes.get("notebooklm_export_sync_headline_ok") is True
