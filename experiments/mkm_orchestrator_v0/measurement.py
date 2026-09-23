from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from .ledger import EventLedger


class MeasurementError(RuntimeError):
    pass


INTEGER_METRIC_FIELDS = (
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

MEAN_METRIC_FIELDS = (
    "review_minutes",
    "task_to_validated_candidate_seconds",
    "worker_cost_usd",
    "evidence_reconstruction_seconds",
)

METRIC_FIELDS = INTEGER_METRIC_FIELDS + MEAN_METRIC_FIELDS

CORE_MEASUREMENT_FIELDS = (
    "review_minutes",
    "task_to_validated_candidate_seconds",
    "worker_cost_usd",
    "evidence_reconstruction_seconds",
)


@dataclass(frozen=True)
class DogfoodMeasurementV0:
    task_id: str
    cohort: str
    measurement_mode: str = "PROSPECTIVE"
    wrong_repo_worktree_incidents: int | None = None
    duplicate_worker_work: int | None = None
    scope_violation_caught: int | None = None
    false_pass_caught: int | None = None
    fresh_fail_caught: int | None = None
    review_minutes: float | None = None
    human_interventions: int | None = None
    rollback_count: int | None = None
    task_to_validated_candidate_seconds: float | None = None
    worker_cost_usd: float | None = None
    builder_pass_validator_fail: int | None = None
    unknown_human_resolutions: int | None = None
    human_gate_rejections: int | None = None
    evidence_reconstruction_seconds: float | None = None

    def validate(self) -> None:
        if not self.task_id.strip():
            raise MeasurementError("task_id required")
        if self.cohort not in {"BASELINE", "EVIDENCE_GATE"}:
            raise MeasurementError("cohort must be BASELINE or EVIDENCE_GATE")
        if self.measurement_mode not in {"PROSPECTIVE", "REPLAY"}:
            raise MeasurementError(
                "measurement_mode must be PROSPECTIVE or REPLAY"
            )
        for name in INTEGER_METRIC_FIELDS:
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise MeasurementError(
                    f"{name} must be a non-negative integer or None"
                )
        for name in MEAN_METRIC_FIELDS:
            value = getattr(self, name)
            if value is None:
                continue
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
            ):
                raise MeasurementError(
                    f"{name} must be non-negative numeric or None"
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
        prospective_rows = [
            r for r in rows
            if r.get("measurement_mode", "PROSPECTIVE") == "PROSPECTIVE"
        ]
        replay_rows = [
            r for r in rows if r.get("measurement_mode") == "REPLAY"
        ]
        cohorts = {
            "BASELINE": [
                r for r in prospective_rows if r.get("cohort") == "BASELINE"
            ],
            "EVIDENCE_GATE": [
                r for r in prospective_rows if r.get("cohort") == "EVIDENCE_GATE"
            ],
        }
        summaries = {
            name: self._cohort_summary(items)
            for name, items in cohorts.items()
        }
        total = len(rows)
        prospective_total = len(prospective_rows)
        replay_total = len(replay_rows)
        both_25 = all(len(items) >= 25 for items in cohorts.values())
        prospective_coverage = self._coverage(prospective_rows)
        core_complete = all(
            prospective_coverage["unknown_count"][name] == 0
            for name in CORE_MEASUREMENT_FIELDS
        )

        if prospective_total < 50:
            readiness = "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
        elif not both_25:
            readiness = "COHORT_BALANCE_NOT_ESTABLISHED"
        elif not core_complete:
            readiness = "MEASUREMENT_COMPLETENESS_NOT_ESTABLISHED"
        else:
            readiness = "READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION"

        return {
            "schema": "mkm_dogfood_summary_v0",
            "measurement_count": total,
            "prospective_measurement_count": prospective_total,
            "replay_measurement_count": replay_total,
            "readiness_basis": "PROSPECTIVE_ONLY",
            "core_measurement_fields": list(CORE_MEASUREMENT_FIELDS),
            "prospective_measurement_coverage": prospective_coverage,
            "cohorts": summaries,
            "replay": self._cohort_summary(replay_rows),
            "readiness": readiness,
            "effectiveness": "NOT_ESTABLISHED",
            "willingness_to_pay": "NOT_ESTABLISHED",
            "pmf": "NOT_ESTABLISHED",
            "automatic_superiority_claim": False,
        }

    def _coverage(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "observed_count": {
                name: sum(1 for row in rows if row.get(name) is not None)
                for name in METRIC_FIELDS
            },
            "unknown_count": {
                name: sum(1 for row in rows if row.get(name) is None)
                for name in METRIC_FIELDS
            },
        }

    def _cohort_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        coverage = self._coverage(rows)
        sums = {}
        for name in INTEGER_METRIC_FIELDS:
            values = [
                int(row[name])
                for row in rows
                if row.get(name) is not None
            ]
            sums[name] = sum(values) if values else None

        means = {}
        for name in MEAN_METRIC_FIELDS:
            values = [
                float(row[name])
                for row in rows
                if row.get(name) is not None
            ]
            means[name] = mean(values) if values else None

        return {
            "count": len(rows),
            "sums": sums,
            "means": means,
            "measurement_coverage": coverage,
        }