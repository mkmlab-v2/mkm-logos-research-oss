from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.cli import main  # noqa: E402
from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.measurement import DogfoodMeasurementV0, MeasurementRecorder  # noqa: E402


def test_cli_shared_publish_and_verify(tmp_path: Path, capsys):
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = EventLedger(ledger_path)
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    shared = tmp_path / "shared"

    assert main([
        "shared-publish",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ]) == 0
    publish_payload = json.loads(capsys.readouterr().out)
    assert publish_payload["view_state"] == "CURRENT_AT_PUBLICATION"

    assert main([
        "shared-verify",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ]) == 0
    verify_payload = json.loads(capsys.readouterr().out)
    assert verify_payload["state"] == "CURRENT"


def test_cli_shared_verify_returns_zero_for_stale_but_reports_stale(tmp_path: Path, capsys):
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = EventLedger(ledger_path)
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    shared = tmp_path / "shared"

    main([
        "shared-publish",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ])
    capsys.readouterr()
    ledger.append("LATER", {"x": 2}, task_id="T")

    assert main([
        "shared-verify",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "STALE"
    assert payload["reason"] == "LEDGER_ADVANCED_SINCE_PUBLICATION"


def test_cli_shared_verify_fails_for_tampered_view(tmp_path: Path, capsys):
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = EventLedger(ledger_path)
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    shared = tmp_path / "shared"

    main([
        "shared-publish",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ])
    capsys.readouterr()
    status_path = shared / "CURRENT_STATUS.json"
    status_path.write_text('{"derived_view":true,"tampered":true}', encoding="utf-8")

    assert main([
        "shared-verify",
        "--ledger", str(ledger_path),
        "--directory", str(shared),
    ]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "INVALID"
    assert payload["reason"] == "STATUS_SHA256_MISMATCH"


def test_cli_dogfood_summary_preserves_not_established(tmp_path: Path, capsys):
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = EventLedger(ledger_path)
    MeasurementRecorder(ledger).record(
        DogfoodMeasurementV0(
            task_id="T",
            cohort="EVIDENCE_GATE",
            review_minutes=5,
        )
    )

    assert main([
        "dogfood-summary",
        "--ledger", str(ledger_path),
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["measurement_count"] == 1
    assert payload["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
    assert payload["effectiveness"] == "NOT_ESTABLISHED"
    assert payload["willingness_to_pay"] == "NOT_ESTABLISHED"
    assert payload["pmf"] == "NOT_ESTABLISHED"
