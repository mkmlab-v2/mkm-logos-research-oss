from __future__ import annotations

from dataclasses import asdict, dataclass, field
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

PROVENANCE_UNKNOWN = "UNKNOWN"
PROVENANCE_OBSERVED = "OBSERVED"
PROVENANCE_NOT_ESTABLISHED = "NOT_ESTABLISHED"


@dataclass(frozen=True)
class MetricProvenanceV0:
    state: str
    value: int | float | None
    capture_source: str = PROVENANCE_NOT_ESTABLISHED
    capture_method: str = PROVENANCE_NOT_ESTABLISHED
    captured_at: str | None = None
    evidence_ref: str | None = None

    def validate(self, *, metric_name: str, metric_value: int | float | None) -> None:
        if self.state not in {PROVENANCE_UNKNOWN, PROVENANCE_OBSERVED}:
            raise MeasurementError(f"{metric_name} provenance state invalid")
        if self.state == PROVENANCE_UNKNOWN:
            if metric_value is not None or self.value is not None:
                raise MeasurementError(f"{metric_name} UNKNOWN provenance conflicts with observed value")
            return
        if metric_value is None:
            raise MeasurementError(f"{metric_name} OBSERVED provenance requires observed metric value")
        if self.value != metric_value:
            raise MeasurementError(f"{metric_name} provenance value mismatch")
        required = {
            "capture_source": self.capture_source,
            "capture_method": self.capture_method,
            "captured_at": self.captured_at,
            "evidence_ref": self.evidence_ref,
        }
        for field_name, raw in required.items():
            if not isinstance(raw, str) or not raw.strip() or raw == PROVENANCE_NOT_ESTABLISHED:
                raise MeasurementError(f"{metric_name} OBSERVED provenance requires {field_name}")


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
    metric_provenance: dict[str, MetricProvenanceV0 | dict[str, Any]] = field(default_factory=dict)

    def _coerce_provenance(self, metric_name: str, raw: MetricProvenanceV0 | dict[str, Any]) -> MetricProvenanceV0:
        if isinstance(raw, MetricProvenanceV0):
            return raw
        if isinstance(raw, dict):
            try:
                return MetricProvenanceV0(**raw)
            except TypeError as exc:
                raise MeasurementError(f"{metric_name} provenance fields invalid") from exc
        raise MeasurementError(f"{metric_name} provenance must be a mapping or MetricProvenanceV0")

    def normalized_metric_provenance(self) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for name in METRIC_FIELDS:
            value = getattr(self, name)
            raw = self.metric_provenance.get(name)
            if raw is None:
                normalized[name] = {
                    "state": PROVENANCE_UNKNOWN if value is None else PROVENANCE_OBSERVED,
                    "value": value,
                    "capture_source": PROVENANCE_NOT_ESTABLISHED,
                    "capture_method": PROVENANCE_NOT_ESTABLISHED,
                    "captured_at": None,
                    "evidence_ref": None,
                }
            else:
                normalized[name] = asdict(self._coerce_provenance(name, raw))
        return normalized

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metric_provenance"] = self.normalized_metric_provenance()
        return payload

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
        unknown_provenance = sorted(set(self.metric_provenance) - set(METRIC_FIELDS))
        if unknown_provenance:
            raise MeasurementError(
                "unknown metric provenance keys: " + ",".join(unknown_provenance)
            )
        for name, raw in self.metric_provenance.items():
            provenance = self._coerce_provenance(name, raw)
            provenance.validate(metric_name=name, metric_value=getattr(self, name))


class MeasurementRecorder:
    SCHEMA = "mkm_dogfood_measurement_v0"

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger

    def record(self, measurement: DogfoodMeasurementV0) -> dict[str, Any]:
        measurement.validate()
        payload = {
            "schema": self.SCHEMA,
            **measurement.to_payload(),
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
        prospective_provenance = self.provenance_coverage(prospective_rows)
        core_complete = all(
            prospective_coverage["unknown_count"][name] == 0
            for name in CORE_MEASUREMENT_FIELDS
        )
        core_provenance_complete = all(
            prospective_provenance["complete_count"][name] == prospective_total
            for name in CORE_MEASUREMENT_FIELDS
        )

        if prospective_total < 50:
            readiness = "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
        elif not both_25:
            readiness = "COHORT_BALANCE_NOT_ESTABLISHED"
        elif not core_complete:
            readiness = "MEASUREMENT_COMPLETENESS_NOT_ESTABLISHED"
        elif not core_provenance_complete:
            readiness = "MEASUREMENT_PROVENANCE_NOT_ESTABLISHED"
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
            "prospective_provenance_coverage": prospective_provenance,
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

    def provenance_coverage(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        def record(row: dict[str, Any], name: str) -> dict[str, Any] | None:
            provenance = row.get("metric_provenance", {})
            if not isinstance(provenance, dict):
                return None
            raw = provenance.get(name)
            return raw if isinstance(raw, dict) else None

        def complete(row: dict[str, Any], name: str) -> bool:
            raw = record(row, name)
            if raw is None:
                return False
            value = row.get(name)
            expected_state = PROVENANCE_UNKNOWN if value is None else PROVENANCE_OBSERVED
            if raw.get("state") != expected_state or raw.get("value") != value:
                return False
            if expected_state == PROVENANCE_UNKNOWN:
                return True
            for field_name in ("capture_source", "capture_method", "captured_at", "evidence_ref"):
                field_value = raw.get(field_name)
                if not isinstance(field_value, str) or not field_value.strip() or field_value == PROVENANCE_NOT_ESTABLISHED:
                    return False
            return True

        return {
            "observed_state_count": {
                name: sum(1 for row in rows if (record(row, name) or {}).get("state") == PROVENANCE_OBSERVED)
                for name in METRIC_FIELDS
            },
            "unknown_state_count": {
                name: sum(1 for row in rows if (record(row, name) or {}).get("state") == PROVENANCE_UNKNOWN)
                for name in METRIC_FIELDS
            },
            "missing_count": {
                name: sum(1 for row in rows if record(row, name) is None)
                for name in METRIC_FIELDS
            },
            "complete_count": {
                name: sum(1 for row in rows if complete(row, name))
                for name in METRIC_FIELDS
            },
            "incomplete_count": {
                name: sum(1 for row in rows if not complete(row, name))
                for name in METRIC_FIELDS
            },
        }

    def _cohort_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        coverage = self._coverage(rows)
        provenance_coverage = self.provenance_coverage(rows)
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
            "provenance_coverage": provenance_coverage,
        }