from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.measurement import DogfoodMeasurementV0  # noqa: E402
from mkm_orchestrator_v0.registry import DogfoodRegistry, DogfoodRegistryError  # noqa: E402


def _finalized(
    task_id: str,
    receipt_id: str,
    *,
    measurement_mode: str = "PROSPECTIVE",
):
    return {
        "task_id": task_id,
        "measurement_mode": measurement_mode,
        "task_state": "CANDIDATE",
        "gate_decision": "HUMAN_GATE",
        "gate_reason": "INDEPENDENT_FRESH_PASS_WITH_BUILDER_PASS",
        "evidence_ceiling": "BOUNDED_MERGE_CANDIDATE",
        "receipt_id": receipt_id,
        "receipt_sha256": "a" * 64,
        "next_action": "HUMAN_GATE",
        "merge_authorization": "NO",
        "deployment_authorization": "NO",
        "send_gate": "HOLD",
    }


def _measurement(
    task_id: str,
    *,
    mode: str = "PROSPECTIVE",
    cohort: str = "EVIDENCE_GATE",
    complete: bool = True,
):
    kwargs = {
        "task_id": task_id,
        "cohort": cohort,
        "measurement_mode": mode,
        "review_minutes": 1,
    }
    if complete:
        kwargs.update({
            "task_to_validated_candidate_seconds": 0,
            "worker_cost_usd": 0,
            "evidence_reconstruction_seconds": 0,
        })
    return DogfoodMeasurementV0(**kwargs)


def test_registry_imports_prospective_task_once(tmp_path: Path):
    ledger = EventLedger(tmp_path / "registry.sqlite3")
    registry = DogfoodRegistry(ledger)
    event = registry.import_finalized(
        _finalized("P-1", "rcp_one"),
        _measurement("P-1"),
    )
    summary = registry.summary()

    assert event["event_type"] == "DOGFOOD_REGISTRY_TASK_IMPORTED"
    assert summary["task_count"] == 1
    assert summary["prospective_task_count"] == 1
    assert summary["replay_task_count"] == 0
    assert summary["prospective_cohorts"]["EVIDENCE_GATE"] == 1
    assert summary["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"


def test_registry_replay_never_inflates_prospective_count(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    registry.import_finalized(
        _finalized("R-1", "rcp_replay", measurement_mode="REPLAY"),
        _measurement("R-1", mode="REPLAY"),
    )
    summary = registry.summary()

    assert summary["task_count"] == 1
    assert summary["prospective_task_count"] == 0
    assert summary["replay_task_count"] == 1
    assert summary["readiness_basis"] == "PROSPECTIVE_ONLY"
    assert summary["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"


def test_registry_rejects_duplicate_task_id(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    registry.import_finalized(_finalized("P-1", "rcp_one"), _measurement("P-1"))

    with pytest.raises(DogfoodRegistryError, match="task_id already imported"):
        registry.import_finalized(
            _finalized("P-1", "rcp_two"),
            _measurement("P-1"),
        )


def test_registry_rejects_duplicate_receipt_id(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    registry.import_finalized(_finalized("P-1", "rcp_same"), _measurement("P-1"))

    with pytest.raises(DogfoodRegistryError, match="receipt_id already imported"):
        registry.import_finalized(
            _finalized("P-2", "rcp_same"),
            _measurement("P-2"),
        )


def test_registry_rejects_mode_mismatch(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))

    with pytest.raises(DogfoodRegistryError, match="measurement_mode mismatch"):
        registry.import_finalized(
            _finalized("P-1", "rcp_one", measurement_mode="REPLAY"),
            _measurement("P-1", mode="PROSPECTIVE"),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("merge_authorization", "YES", "merge authorization"),
        ("deployment_authorization", "YES", "deployment authorization"),
        ("send_gate", "ALLOW", "send gate"),
    ],
)
def test_registry_rejects_open_authorization_boundaries(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    finalized = _finalized("P-1", "rcp_one")
    finalized[field] = value

    with pytest.raises(DogfoodRegistryError, match=message):
        registry.import_finalized(finalized, _measurement("P-1"))


def test_registry_is_append_only_and_hash_chain_valid(tmp_path: Path):
    ledger = EventLedger(tmp_path / "registry.sqlite3")
    registry = DogfoodRegistry(ledger)
    registry.import_finalized(_finalized("P-1", "rcp_one"), _measurement("P-1"))

    assert registry.summary()["registry_integrity"]["valid"] is True
    con = sqlite3.connect(ledger.path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE events SET event_type='X' WHERE seq=1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM events WHERE seq=1")
    con.close()


def test_balanced_50_is_only_ready_for_human_adjudication(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    for i in range(25):
        registry.import_finalized(
            _finalized(f"B-{i}", f"rcp_b_{i}"),
            _measurement(f"B-{i}", cohort="BASELINE"),
        )
        registry.import_finalized(
            _finalized(f"E-{i}", f"rcp_e_{i}"),
            _measurement(f"E-{i}", cohort="EVIDENCE_GATE"),
        )

    summary = registry.summary()
    assert summary["prospective_task_count"] == 50
    assert summary["readiness"] == "READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"
    assert summary["willingness_to_pay"] == "NOT_ESTABLISHED"
    assert summary["pmf"] == "NOT_ESTABLISHED"
    assert summary["automatic_superiority_claim"] is False


def test_registry_preserves_unknown_core_measurements(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    registry.import_finalized(
        _finalized("U-1", "rcp_unknown"),
        _measurement("U-1", complete=False),
    )
    summary = registry.summary()

    coverage = summary["prospective_measurement_coverage"]
    assert coverage["observed_count"]["review_minutes"] == 1
    assert coverage["unknown_count"]["worker_cost_usd"] == 1
    assert coverage["unknown_count"]["task_to_validated_candidate_seconds"] == 1


def test_registry_balanced_50_unknown_core_metrics_blocks_readiness(tmp_path: Path):
    registry = DogfoodRegistry(EventLedger(tmp_path / "registry.sqlite3"))
    for i in range(25):
        registry.import_finalized(
            _finalized(f"BU-{i}", f"rcp_bu_{i}"),
            _measurement(f"BU-{i}", cohort="BASELINE", complete=False),
        )
        registry.import_finalized(
            _finalized(f"EU-{i}", f"rcp_eu_{i}"),
            _measurement(f"EU-{i}", cohort="EVIDENCE_GATE", complete=False),
        )

    summary = registry.summary()
    assert summary["prospective_task_count"] == 50
    assert summary["readiness"] == "MEASUREMENT_COMPLETENESS_NOT_ESTABLISHED"
    assert summary["prospective_measurement_coverage"]["unknown_count"]["worker_cost_usd"] == 50
    assert summary["effectiveness"] == "NOT_ESTABLISHED"