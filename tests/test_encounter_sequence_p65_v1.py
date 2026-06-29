"""TKM encounter_sequence P65 post-ultra-grand passive observation gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p65_gate_v1_latest.json"
OBS = ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p65_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p65 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p65_status") == "post_ultra_grand_passive_observation_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_post_ultra_grand_passive_observation() -> None:
    if not OBS.is_file():
        pytest.skip("post ultra grand passive observation missing")
    doc = json.loads(OBS.read_text(encoding="utf-8-sig"))
    assert doc.get("observation_ok") is True
    assert doc.get("ultra_grand_export_bundle_vault_sync_ok") is True
    assert doc.get("ultra_grand_post_export_closure_ok") is True
    assert doc.get("passive_observation_ok") is True
    assert doc.get("export_ingest_kpi_ok") is True
    assert doc.get("curated_milestone_ok") is True
    assert doc.get("weekly_task_ready") is True
    assert ARTIFACT.is_file()


def test_weekly_post_ultra_grand_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("5.1.0", "5.2.0", "5.3.0")
    pug = doc.get("post_ultra_grand_passive_observation_kpi")
    assert isinstance(pug, dict)
    assert pug.get("post_ultra_grand_passive_observation_headline_ok") is True
