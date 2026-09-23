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
CAPTURE_BASIS_IN_TASK = "IN_TASK_OBSERVATION"
CAPTURE_BASIS_POST_HOC = "POST_HOC_RECONSTRUCTION"

COMMON_METRIC_CONTRACT = (
    "task_to_validated_candidate_seconds",
    "review_minutes",
    "worker_cost_usd",
    "evidence_reconstruction_seconds",
    "wrong_repo_worktree_incidents",
    "duplicate_worker_work",
    "scope_violation_caught",
    "builder_pass_validator_fail",
    "false_pass_caught",
    "fresh_fail_caught",
    "human_interventions",
    "human_gate_rejections",
    "rollback_count",
    "unknown_human_resolutions",
)


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
class MeasurementCaptureContextV0:
    task_id: str
    base_revision: str
    worktree_path: str
    observer_id: str
    measurement_method: str
    measured_at: str
    capture_basis: str

    def validate(self, *, task_id: str, measurement_mode: str) -> None:
        required = {
            "task_id": self.task_id,
            "base_revision": self.base_revision,
            "worktree_path": self.worktree_path,
            "observer_id": self.observer_id,
            "measurement_method": self.measurement_method,
            "measured_at": self.measured_at,
        }
        for field_name, raw in required.items():
            if not isinstance(raw, str) or not raw.strip():
                raise MeasurementError(f"capture_context {field_name} required")
        if self.task_id != task_id:
            raise MeasurementError("capture_context task_id mismatch")
        if self.capture_basis not in {
            CAPTURE_BASIS_IN_TASK,
            CAPTURE_BASIS_POST_HOC,
        }:
            raise MeasurementError("capture_context capture_basis invalid")
        if measurement_mode == "PROSPECTIVE" and self.capture_basis != CAPTURE_BASIS_IN_TASK:
            raise MeasurementError("prospective measurement requires IN_TASK_OBSERVATION")
        if self.capture_basis == CAPTURE_BASIS_POST_HOC and measurement_mode != "REPLAY":
            raise MeasurementError("POST_HOC_RECONSTRUCTION must be REPLAY")


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
    capture_context: MeasurementCaptureContextV0 | dict[str, Any] | None = None

    def _coerce_capture_context(self) -> MeasurementCaptureContextV0 | None:
        if self.capture_context is None:
            return None
        if isinstance(self.capture_context, MeasurementCaptureContextV0):
            return self.capture_context
        if isinstance(self.capture_context, dict):
            try:
                return MeasurementCaptureContextV0(**self.capture_context)
            except TypeError as exc:
                raise MeasurementError("capture_context fields invalid") from exc
        raise MeasurementError("capture_context must be a mapping or MeasurementCaptureContextV0")

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
        context = self._coerce_capture_context()
        payload["capture_context"] = asdict(context) if context is not None else None
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

        context = self._coerce_capture_context()
        if context is not None:
            context.validate(task_id=self.task_id, measurement_mode=self.measurement_mode)

        if self.cohort == "BASELINE":
            if context is None:
                raise MeasurementError("BASELINE capture_context required")
            for name in METRIC_FIELDS:
                value = getattr(self, name)
                if value is None:
                    continue
                raw = self.metric_provenance.get(name)
                if raw is None:
                    raise MeasurementError(
                        f"BASELINE observed {name} requires explicit provenance"
                    )
                provenance = self._coerce_provenance(name, raw)
                provenance.validate(metric_name=name, metric_value=value)


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
        cohort_rows = {
            "BASELINE": [r for r in rows if r.get("cohort") == "BASELINE"],
            "EVIDENCE_GATE": [r for r in rows if r.get("cohort") == "EVIDENCE_GATE"],
        }
        cohorts = {
            name: [
                r for r in items
                if r.get("measurement_mode", "PROSPECTIVE") == "PROSPECTIVE"
            ]
            for name, items in cohort_rows.items()
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
        cohort_capture = {
            name: self.capture_protocol_summary(items)
            for name, items in cohort_rows.items()
        }
        comparison_readiness = self._comparison_readiness(cohort_capture)
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
        elif min(
            cohort_capture["BASELINE"]["comparable_prospective_count"],
            cohort_capture["EVIDENCE_GATE"]["comparable_prospective_count"],
        ) < 25:
            readiness = "COMPARABLE_MEASUREMENT_NOT_ESTABLISHED"
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
            "cohort_capture_protocol": cohort_capture,
            "comparison_readiness": comparison_readiness,
            "comparability": "NOT_ESTABLISHED",
            "common_metric_contract": list(COMMON_METRIC_CONTRACT),
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

    def capture_context_complete(self, row: dict[str, Any]) -> bool:
        context = row.get("capture_context")
        if not isinstance(context, dict):
            return False
        required = (
            "task_id",
            "base_revision",
            "worktree_path",
            "observer_id",
            "measurement_method",
            "measured_at",
            "capture_basis",
        )
        if any(not isinstance(context.get(name), str) or not context[name].strip() for name in required):
            return False
        if context["task_id"] != row.get("task_id"):
            return False
        mode = row.get("measurement_mode", "PROSPECTIVE")
        basis = context["capture_basis"]
        if mode == "PROSPECTIVE" and basis != CAPTURE_BASIS_IN_TASK:
            return False
        if basis == CAPTURE_BASIS_POST_HOC and mode != "REPLAY":
            return False
        return basis in {CAPTURE_BASIS_IN_TASK, CAPTURE_BASIS_POST_HOC}

    def is_fully_comparable(self, row: dict[str, Any]) -> bool:
        if row.get("measurement_mode", "PROSPECTIVE") != "PROSPECTIVE":
            return False
        if not self.capture_context_complete(row):
            return False
        if any(row.get(name) is None for name in COMMON_METRIC_CONTRACT):
            return False
        provenance = self.provenance_coverage([row])
        return all(
            provenance["complete_count"][name] == 1
            for name in COMMON_METRIC_CONTRACT
        )

    def capture_protocol_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        prospective = [
            row for row in rows
            if row.get("measurement_mode", "PROSPECTIVE") == "PROSPECTIVE"
        ]
        replay = [row for row in rows if row.get("measurement_mode") == "REPLAY"]
        return {
            "prospective_count": len(prospective),
            "replay_count": len(replay),
            "capture_context_complete_count": sum(
                1 for row in rows if self.capture_context_complete(row)
            ),
            "capture_context_missing_count": sum(
                1 for row in rows if not self.capture_context_complete(row)
            ),
            "comparable_prospective_count": sum(
                1 for row in prospective if self.is_fully_comparable(row)
            ),
        }

    @staticmethod
    def _comparison_readiness(cohort_capture: dict[str, dict[str, Any]]) -> str:
        baseline = cohort_capture["BASELINE"]
        evidence = cohort_capture["EVIDENCE_GATE"]
        if baseline["prospective_count"] == 0:
            return "BASELINE_SAMPLE_NOT_ESTABLISHED"
        if evidence["prospective_count"] == 0:
            return "EVIDENCE_GATE_SAMPLE_NOT_ESTABLISHED"
        if min(
            baseline["comparable_prospective_count"],
            evidence["comparable_prospective_count"],
        ) == 0:
            return "COMPARABLE_MEASUREMENT_NOT_ESTABLISHED"
        if min(
            baseline["comparable_prospective_count"],
            evidence["comparable_prospective_count"],
        ) < 25:
            return "INSUFFICIENT_COMPARABLE_SAMPLE_LT_25_PER_COHORT"
        return "READY_FOR_HUMAN_COMPARISON_ADJUDICATION"

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