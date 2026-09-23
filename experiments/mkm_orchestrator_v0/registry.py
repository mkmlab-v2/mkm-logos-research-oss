from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import json
import re
from typing import Any

from .ledger import EventLedger
from .measurement import (
    COMMON_METRIC_CONTRACT,
    CORE_MEASUREMENT_FIELDS,
    METRIC_FIELDS,
    DogfoodMeasurementV0,
    MeasurementRecorder,
)


class DogfoodRegistryError(RuntimeError):
    pass


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DogfoodRegistry:
    """Persistent cross-task registry for finalized dogfood outcomes.

    The registry accepts normalized task-finalization records and measurements
    into an append-only EventLedger. REPLAY records remain visible but never
    contribute to prospective effectiveness readiness.
    """

    EVENT_TYPE = "DOGFOOD_REGISTRY_TASK_IMPORTED"
    SCHEMA = "mkm_dogfood_registry_task_v0"

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def import_finalized(
        self,
        finalized: dict[str, Any],
        measurement: DogfoodMeasurementV0,
    ) -> dict[str, Any]:
        measurement.validate()
        task_id = finalized.get("task_id")
        if not task_id or task_id != measurement.task_id:
            raise DogfoodRegistryError("task_id mismatch")
        mode = finalized.get("measurement_mode")
        if mode != measurement.measurement_mode:
            raise DogfoodRegistryError("measurement_mode mismatch")
        if measurement.cohort not in {"BASELINE", "EVIDENCE_GATE"}:
            raise DogfoodRegistryError("invalid cohort")

        receipt_id = finalized.get("receipt_id")
        receipt_sha256 = finalized.get("receipt_sha256")
        if not isinstance(receipt_id, str) or not receipt_id.startswith("rcp_"):
            raise DogfoodRegistryError("receipt_id invalid")
        if not isinstance(receipt_sha256, str) or not _SHA256.fullmatch(receipt_sha256):
            raise DogfoodRegistryError("receipt_sha256 invalid")

        if finalized.get("merge_authorization") != "NO":
            raise DogfoodRegistryError("merge authorization must remain NO")
        if finalized.get("deployment_authorization") != "NO":
            raise DogfoodRegistryError("deployment authorization must remain NO")
        if finalized.get("send_gate") != "HOLD":
            raise DogfoodRegistryError("send gate must remain HOLD")

        allowed_states = {"HOLD", "CANDIDATE", "FAIL"}
        if finalized.get("task_state") not in allowed_states:
            raise DogfoodRegistryError("task_state invalid")
        allowed_decisions = {"HOLD", "HUMAN_GATE", "DENY"}
        if finalized.get("gate_decision") not in allowed_decisions:
            raise DogfoodRegistryError("gate_decision invalid")

        existing = self._records()
        if any(row["task_id"] == task_id for row in existing):
            raise DogfoodRegistryError("task_id already imported")
        if any(row["receipt_id"] == receipt_id for row in existing):
            raise DogfoodRegistryError("receipt_id already imported")

        measurement_payload = measurement.to_payload()
        payload = {
            "schema": self.SCHEMA,
            "task_id": task_id,
            "cohort": measurement.cohort,
            "measurement_mode": measurement.measurement_mode,
            "receipt_id": receipt_id,
            "receipt_sha256": receipt_sha256,
            "task_state": finalized["task_state"],
            "gate_decision": finalized["gate_decision"],
            "gate_reason": finalized.get("gate_reason", "UNKNOWN"),
            "evidence_ceiling": finalized.get(
                "evidence_ceiling", "NOT_ADJUDICATED"
            ),
            "next_action": finalized.get("next_action", "HOLD"),
            "measurement": measurement_payload,
            "measurement_sha256": _digest(measurement_payload),
            "merge_authorization": "NO",
            "deployment_authorization": "NO",
            "send_gate": "HOLD",
        }
        return self.ledger.append(
            self.EVENT_TYPE,
            payload,
            task_id=task_id,
        )

    def summary(self) -> dict[str, Any]:
        rows = self._records()
        prospective = [
            row for row in rows if row["measurement_mode"] == "PROSPECTIVE"
        ]
        replay = [
            row for row in rows if row["measurement_mode"] == "REPLAY"
        ]
        cohorts = {
            "BASELINE": sum(
                1 for row in prospective if row["cohort"] == "BASELINE"
            ),
            "EVIDENCE_GATE": sum(
                1 for row in prospective if row["cohort"] == "EVIDENCE_GATE"
            ),
        }
        recorder = MeasurementRecorder(self.ledger)
        measurement_rows = [row.get("measurement", {}) for row in prospective]
        cohort_measurements = {
            "BASELINE": [
                row.get("measurement", {})
                for row in rows
                if row["cohort"] == "BASELINE"
            ],
            "EVIDENCE_GATE": [
                row.get("measurement", {})
                for row in rows
                if row["cohort"] == "EVIDENCE_GATE"
            ],
        }
        coverage = {
            "observed_count": {
                name: sum(
                    1
                    for row in prospective
                    if row.get("measurement", {}).get(name) is not None
                )
                for name in METRIC_FIELDS
            },
            "unknown_count": {
                name: sum(
                    1
                    for row in prospective
                    if row.get("measurement", {}).get(name) is None
                )
                for name in METRIC_FIELDS
            },
        }
        provenance_coverage = recorder.provenance_coverage(measurement_rows)
        cohort_capture = {
            name: recorder.capture_protocol_summary(items)
            for name, items in cohort_measurements.items()
        }
        cohort_coverage = {
            name: {
                "measurement_coverage": recorder._coverage([
                    row for row in items
                    if row.get("measurement_mode", "PROSPECTIVE") == "PROSPECTIVE"
                ]),
                "provenance_coverage": recorder.provenance_coverage([
                    row for row in items
                    if row.get("measurement_mode", "PROSPECTIVE") == "PROSPECTIVE"
                ]),
            }
            for name, items in cohort_measurements.items()
        }
        comparison_readiness = recorder._comparison_readiness(cohort_capture)
        core_complete = all(
            coverage["unknown_count"][name] == 0
            for name in CORE_MEASUREMENT_FIELDS
        )
        core_provenance_complete = all(
            provenance_coverage["complete_count"][name] == len(prospective)
            for name in CORE_MEASUREMENT_FIELDS
        )
        if len(prospective) < 50:
            readiness = "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
        elif min(cohorts.values()) < 25:
            readiness = "COHORT_BALANCE_NOT_ESTABLISHED"
        elif not core_complete:
            readiness = "MEASUREMENT_COMPLETENESS_NOT_ESTABLISHED"
        elif not core_provenance_complete:
            readiness = "MEASUREMENT_PROVENANCE_NOT_ESTABLISHED"
        elif min(
            cohort_capture["BASELINE"]["comparable_prospective_count"],
            cohort_capture["EVIDENCE_GATE"]["comparable_prospective_count"],
        ) < 25:
            readiness = "COMPARABLE_MEASUREMENT_NOT_ESTABLISHED"
        else:
            readiness = "READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION"

        return {
            "schema": "mkm_dogfood_registry_summary_v0",
            "registry_integrity": self.ledger.verify_chain(),
            "task_count": len(rows),
            "prospective_task_count": len(prospective),
            "replay_task_count": len(replay),
            "prospective_cohorts": cohorts,
            "task_states": dict(sorted(Counter(
                row["task_state"] for row in rows
            ).items())),
            "gate_decisions": dict(sorted(Counter(
                row["gate_decision"] for row in rows
            ).items())),
            "readiness_basis": "PROSPECTIVE_ONLY",
            "core_measurement_fields": list(CORE_MEASUREMENT_FIELDS),
            "prospective_measurement_coverage": coverage,
            "prospective_provenance_coverage": provenance_coverage,
            "prospective_cohort_coverage": cohort_coverage,
            "cohort_capture_protocol": cohort_capture,
            "comparison_readiness": comparison_readiness,
            "comparability": "NOT_ESTABLISHED",
            "common_metric_contract": list(COMMON_METRIC_CONTRACT),
            "readiness": readiness,
            "effectiveness": "NOT_ESTABLISHED",
            "willingness_to_pay": "NOT_ESTABLISHED",
            "pmf": "NOT_ESTABLISHED",
            "automatic_superiority_claim": False,
            "merge_authorization": "NO",
            "deployment_authorization": "NO",
            "send_gate": "HOLD",
        }

    def _records(self) -> list[dict[str, Any]]:
        return [
            event["payload"]
            for event in self.ledger.events()
            if event["event_type"] == self.EVENT_TYPE
            and event["payload"].get("schema") == self.SCHEMA
        ]