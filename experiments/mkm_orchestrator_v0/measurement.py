from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from .ledger import EventLedger


class MeasurementError(RuntimeError):
    pass


@dataclass(frozen=True)
class DogfoodMeasurementV0:
    task_id: str
    cohort: str
    wrong_repo_worktree_incidents: int = 0
    duplicate_worker_work: int = 0
    scope_violation_caught: int = 0
    false_pass_caught: int = 0
    fresh_fail_caught: int = 0
    review_minutes: float = 0.0
    human_interventions: int = 0
    rollback_count: int = 0
    task_to_validated_candidate_seconds: float | None = None
    worker_cost_usd: float = 0.0
    builder_pass_validator_fail: int = 0
    unknown_human_resolutions: int = 0
    human_gate_rejections: int = 0
    evidence_reconstruction_seconds: float = 0.0

    def validate(self) -> None:
        if not self.task_id.strip():
            raise MeasurementError("task_id required")
        if self.cohort not in {"BASELINE", "EVIDENCE_GATE"}:
            raise MeasurementError("cohort must be BASELINE or EVIDENCE_GATE")
        integer_fields = (
            "wrong_repo_worktree_incidents",
            "duplicate_worker_work",
            "scope_violation_caught",
            "false_pass_caught",
            "fresh_fail_caught",
            "human_interventions",
            "rollback_count",
            "builder_pass_validator_fail",
            "unknown_human_resolutions",
            "human_gate_rejections",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise MeasurementError(f"{name} must be a non-negative integer")
        float_fields = (
            "review_minutes",
            "worker_cost_usd",
            "evidence_reconstruction_seconds",
        )
        for name in float_fields:
            value = getattr(self, name)
            if value < 0:
                raise MeasurementError(f"{name} must be non-negative")
        if (
            self.task_to_validated_candidate_seconds is not None
            and self.task_to_validated_candidate_seconds < 0
        ):
            raise MeasurementError(
                "task_to_validated_candidate_seconds must be non-negative or None"
            )


class MeasurementRecorder:
    SCHEMA = "mkm_dogfood_measurement_v0"

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def record(self, measurement: DogfoodMeasurementV0) -> dict[str, Any]:
        measurement.validate()
        payload = {
            "schema": self.SCHEMA,
            **asdict(measurement),
        }
        return self.ledger.append(
            "TASK_MEASUREMENT_RECORDED",
            payload,
            task_id=measurement.task_id,
        )

    def summarize(self) -> dict[str, Any]:
        rows = [
            r["payload"]
            for r in self.ledger.events()
            if r["event_type"] == "TASK_MEASUREMENT_RECORDED"
            and r["payload"].get("schema") == self.SCHEMA
        ]
        cohorts = {
            "BASELINE": [r for r in rows if r.get("cohort") == "BASELINE"],
            "EVIDENCE_GATE": [r for r in rows if r.get("cohort") == "EVIDENCE_GATE"],
        }
        summaries = {
            name: self._cohort_summary(items)
            for name, items in cohorts.items()
        }
        total = len(rows)
        both_25 = all(len(items) >= 25 for items in cohorts.values())
        if total < 50:
            readiness = "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
        elif not both_25:
            readiness = "COHORT_BALANCE_NOT_ESTABLISHED"
        else:
            readiness = "READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION"

        return {
            "schema": "mkm_dogfood_summary_v0",
            "measurement_count": total,
            "cohorts": summaries,
            "readiness": readiness,
            "effectiveness": "NOT_ESTABLISHED",
            "willingness_to_pay": "NOT_ESTABLISHED",
            "pmf": "NOT_ESTABLISHED",
            "automatic_superiority_claim": False,
        }

    def _cohort_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {
                "count": 0,
                "sums": {},
                "means": {},
            }
        sum_fields = (
            "wrong_repo_worktree_incidents",
            "duplicate_worker_work",
            "scope_violation_caught",
            "false_pass_caught",
            "fresh_fail_caught",
            "human_interventions",
            "rollback_count",
            "builder_pass_validator_fail",
            "unknown_human_resolutions",
            "human_gate_rejections",
        )
        mean_fields = (
            "review_minutes",
            "worker_cost_usd",
            "evidence_reconstruction_seconds",
        )
        candidate_times = [
            r["task_to_validated_candidate_seconds"]
            for r in rows
            if r.get("task_to_validated_candidate_seconds") is not None
        ]
        return {
            "count": len(rows),
            "sums": {
                name: sum(int(r[name]) for r in rows)
                for name in sum_fields
            },
            "means": {
                **{
                    name: mean(float(r[name]) for r in rows)
                    for name in mean_fields
                },
                "task_to_validated_candidate_seconds": (
                    mean(candidate_times) if candidate_times else None
                ),
            },
        }
