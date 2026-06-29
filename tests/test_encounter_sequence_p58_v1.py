"""TKM encounter_sequence P58 grand export bundle vault sync gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p58_gate_v1_latest.json"
SYNC = ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_export_manifest_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p58_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p58 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p58_status") == "grand_export_bundle_vault_sync_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_grand_export_bundle_vault_sync() -> None:
    if not SYNC.is_file():
        pytest.skip("grand export bundle vault sync missing")
    doc = json.loads(SYNC.read_text(encoding="utf-8-sig"))
    assert doc.get("grand_export_bundle_vault_sync_ok") is True
    assert doc.get("cloud_upload_forbidden") is True
    assert doc.get("cloud_upload_attempted") is False
    assert int(doc.get("manifest_files_present_count") or 0) >= 16
    assert doc.get("grand_post_export_closure_ok") is True
    assert doc.get("base_export_sync_ok") is True
    assert ARTIFACT.is_file()
    assert MANIFEST.is_file()


def test_weekly_grand_export_vault_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("4.4.0", "4.5.0", "4.6.0")
    geb = doc.get("grand_export_bundle_vault_sync_kpi")
    assert isinstance(geb, dict)
    assert geb.get("grand_export_bundle_vault_sync_headline_ok") is True
