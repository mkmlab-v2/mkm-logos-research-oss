"""TKM encounter_sequence post-P68 maintenance (drift obs + curated bulk review) smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "reports/tkm_encounter_sequence_post_p68_maintenance_chain_v1_latest.json"
DRIFT = ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
DRIFT_ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
BULK = ROOT / "reports/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
BULK_ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_post_p68_maintenance_chain() -> None:
    if not CHAIN.is_file():
        pytest.skip("post p68 maintenance chain missing")
    doc = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    assert doc.get("post_p68_maintenance_ok") is True
    assert doc.get("tier_inflation_forbidden") is True
    assert doc.get("send_gate") == "HOLD"


def test_post_breakpoint_passive_drift_observation() -> None:
    if not DRIFT.is_file():
        pytest.skip("post breakpoint passive drift observation missing")
    doc = json.loads(DRIFT.read_text(encoding="utf-8-sig"))
    assert doc.get("observation_ok") is True
    assert doc.get("ultra_grand_stack_breakpoint_freeze") is True
    assert doc.get("drift_regression_detected") is False
    assert doc.get("tier_inflation_forbidden") is True
    assert DRIFT_ARTIFACT.is_file()


def test_curated_bulk_human_review() -> None:
    if not BULK.is_file():
        pytest.skip("curated bulk human review missing")
    doc = json.loads(BULK.read_text(encoding="utf-8-sig"))
    assert doc.get("bulk_human_review_ok") is True
    assert int(doc.get("curated_reviewed_count") or 0) >= 6
    assert doc.get("human_gate_ack_ok") is True
    assert doc.get("tier_inflation_forbidden") is True
    assert BULK_ARTIFACT.is_file()


def test_weekly_post_p68_maintenance_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("5.5.0", "5.6.0")
    drift_kpi = doc.get("post_breakpoint_passive_drift_observation_kpi")
    bulk_kpi = doc.get("curated_bulk_human_review_kpi")
    assert isinstance(drift_kpi, dict)
    assert isinstance(bulk_kpi, dict)
    assert drift_kpi.get("post_breakpoint_passive_drift_headline_ok") is True
    assert bulk_kpi.get("curated_bulk_human_review_headline_ok") is True
