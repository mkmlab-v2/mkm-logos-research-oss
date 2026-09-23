from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.measurement import (  # noqa: E402
    COMMON_METRIC_CONTRACT,
    DogfoodMeasurementV0,
    MeasurementCaptureContextV0,
    MeasurementError,
    MeasurementRecorder,
    MetricProvenanceV0,
)
from mkm_orchestrator_v0.models import (  # noqa: E402
    AuthorityContract,
    EvidenceFreshness,
    EvidenceOutcome,
    TaskContract,
    TaskState,
    WorkerResult,
)
from mkm_orchestrator_v0.orchestrator import MKMOrchestrator  # noqa: E402
from mkm_orchestrator_v0.receipt import observe_workspace  # noqa: E402
from mkm_orchestrator_v0.validator import (  # noqa: E402
    IndependentValidatorContract,
    ValidationContractError,
)
from mkm_orchestrator_v0.workspace import WorktreeManager  # noqa: E402


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def _setup(tmp_path: Path):
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "MKM Validator Fixture")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()

    task = TaskContract(
        task_id="VAL-001",
        objective="Validator fixture",
        authority=AuthorityContract(
            repository_id="fixture",
            repository_path=str(repo),
            base_revision=head,
            source_kind="AUTHORITATIVE",
            mutation_authorized=True,
        ),
        allowed_paths=("app.py",),
        required_suites=("validator-suite",),
    )
    ledger = EventLedger(tmp_path / "state" / "ledger.sqlite3")
    orch = MKMOrchestrator(
        ledger=ledger,
        worktrees=WorktreeManager(tmp_path / "worktrees"),
    )
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    root = Path(binding.worktree_path)
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    observed = observe_workspace(root)
    result = WorkerResult(
        worker_id="builder-1",
        task_id=task.task_id,
        status="PASS",
        subject_digest=observed["subject_digest"],
        changed_files=tuple(observed["changed_files"]),
        summary="fixture",
        metadata={"backend": "fixture"},
    )
    ledger.append(
        "WORKER_STARTED",
        {
            "worker_id": result.worker_id,
            "worktree_path": binding.worktree_path,
            "base_revision": binding.base_revision,
        },
        task_id=task.task_id,
    )
    ledger.append(
        "WORKER_RESULT",
        {
            "worker_id": result.worker_id,
            "status": result.status,
            "subject_digest": result.subject_digest,
            "changed_files": list(result.changed_files),
            "summary": result.summary,
            "metadata": result.metadata,
            "evidence_state": "WORKER_CLAIM_ONLY",
        },
        task_id=task.task_id,
    )
    orch.record_builder_evidence(
        result,
        suite_id="builder-suite",
        suite_digest="a" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "builder pass"},
    )
    return ledger, orch, task, binding, result


def _validator_kwargs(result):
    return {
        "task_id": result.task_id,
        "validator_id": "validator-1",
        "suite_id": "validator-suite",
        "suite_digest": "b" * 64,
        "subject_digest": result.subject_digest,
        "returncode": 0,
        "stdout_sha256": "c" * 64,
        "stderr_sha256": "d" * 64,
        "duration_ms": 100,
    }


def _observed_provenance(**values):
    return {
        name: MetricProvenanceV0(
            state="OBSERVED",
            value=value,
            capture_source="fixture",
            capture_method="fixture-observation",
            captured_at="2026-09-23T00:00:00Z",
            evidence_ref=f"fixture:{name}",
        )
        for name, value in values.items()
    }


def _capture_context(task_id: str, *, capture_basis: str = "IN_TASK_OBSERVATION"):
    return MeasurementCaptureContextV0(
        task_id=task_id,
        base_revision="a" * 40,
        worktree_path=f"/fixture/{task_id}",
        observer_id="fixture-observer",
        measurement_method="fixture-observation",
        measured_at="2026-09-23T00:00:00Z",
        capture_basis=capture_basis,
    )


def _complete_capture(task_id: str, **overrides):
    values = {name: 0 for name in COMMON_METRIC_CONTRACT}
    values.update(overrides)
    return {
        **values,
        "metric_provenance": _observed_provenance(**values),
        "capture_context": _capture_context(task_id),
    }


def test_validator_identity_must_differ_from_builder(tmp_path: Path):
    ledger, _orch, _task, _binding, result = _setup(tmp_path)
    validator = IndependentValidatorContract(ledger)
    args = _validator_kwargs(result)
    args["validator_id"] = "builder-1"

    with pytest.raises(
        ValidationContractError,
        match="BUILDER_VALIDATOR_IDENTITY_COLLISION",
    ):
        validator.record_test_result(**args)

    assert ledger.events(task_id=result.task_id)[-1]["event_type"] == "VALIDATION_REJECTED"


def test_validator_rejects_subject_drift(tmp_path: Path):
    ledger, _orch, _task, binding, result = _setup(tmp_path)
    (Path(binding.worktree_path) / "app.py").write_text("VALUE = 3\n", encoding="utf-8")

    with pytest.raises(ValidationContractError, match="SUBJECT_DIGEST_DRIFT"):
        IndependentValidatorContract(ledger).record_test_result(
            **_validator_kwargs(result)
        )


def test_validator_rejects_changed_path_outside_contract(tmp_path: Path):
    ledger, _orch, _task, binding, result = _setup(tmp_path)
    root = Path(binding.worktree_path)
    (root / "forbidden.txt").write_text("nope\n", encoding="utf-8")
    observed = observe_workspace(root)
    args = _validator_kwargs(result)
    args["subject_digest"] = observed["subject_digest"]

    with pytest.raises(
        ValidationContractError,
        match="CHANGED_PATH_OUTSIDE_TASK_CONTRACT",
    ):
        IndependentValidatorContract(ledger).record_test_result(**args)

    rejected = ledger.events(task_id=result.task_id)[-1]
    assert rejected["event_type"] == "VALIDATION_REJECTED"
    assert rejected["payload"]["violations"] == ["forbidden.txt"]


def test_validator_pass_is_independent_fresh_and_keeps_authorization_closed(tmp_path: Path):
    ledger, orch, _task, _binding, result = _setup(tmp_path)
    record = IndependentValidatorContract(ledger).record_test_result(
        **_validator_kwargs(result)
    )
    gate = orch.evaluate(result.task_id)

    assert record.outcome == EvidenceOutcome.PASS
    assert record.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    assert gate.task_state == TaskState.CANDIDATE
    assert gate.merge_authorization == "NO"
    assert gate.deployment_authorization == "NO"
    assert gate.send_gate == "HOLD"


def test_validator_nonzero_returncode_records_fresh_fail_and_seals_gate(tmp_path: Path):
    ledger, orch, _task, _binding, result = _setup(tmp_path)
    args = _validator_kwargs(result)
    args["returncode"] = 1
    record = IndependentValidatorContract(ledger).record_test_result(**args)
    gate = orch.evaluate(result.task_id)

    assert record.outcome == EvidenceOutcome.FAIL
    assert record.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    assert gate.task_state == TaskState.FAIL
    assert gate.reason == "SEALED_INDEPENDENT_FRESH_FAIL"


def test_repeated_validator_artifact_is_not_fresh(tmp_path: Path):
    ledger, _orch, _task, _binding, result = _setup(tmp_path)
    validator = IndependentValidatorContract(ledger)
    first = validator.record_test_result(**_validator_kwargs(result))
    second = validator.record_test_result(**_validator_kwargs(result))

    assert first.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    assert second.freshness == EvidenceFreshness.REPEAT_OBSERVATION


def test_measurement_rejects_negative_values(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="review_minutes"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="T",
                cohort="BASELINE",
                review_minutes=-1,
            )
        )


def test_dogfood_under_50_stays_not_established(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    for i in range(10):
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"T-{i}",
                cohort="EVIDENCE_GATE",
                review_minutes=5,
                worker_cost_usd=1,
            )
        )
    summary = recorder.summarize()

    assert summary["measurement_count"] == 10
    assert summary["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"
    assert summary["automatic_superiority_claim"] is False


def test_balanced_50_tasks_are_only_ready_for_human_adjudication(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    for i in range(25):
        task_id = f"B-{i}"
        recorder.record(
            DogfoodMeasurementV0(
                task_id=task_id,
                cohort="BASELINE",
                **_complete_capture(
                    task_id,
                    wrong_repo_worktree_incidents=1 if i < 3 else 0,
                    review_minutes=20,
                    worker_cost_usd=2,
                    builder_pass_validator_fail=1 if i < 4 else 0,
                ),
            )
        )
    for i in range(25):
        task_id = f"E-{i}"
        recorder.record(
            DogfoodMeasurementV0(
                task_id=task_id,
                cohort="EVIDENCE_GATE",
                **_complete_capture(
                    task_id,
                    review_minutes=10,
                    worker_cost_usd=2.5,
                    builder_pass_validator_fail=1 if i < 2 else 0,
                    false_pass_caught=1 if i < 2 else 0,
                ),
            )
        )
    summary = recorder.summarize()

    assert summary["measurement_count"] == 50
    assert summary["cohorts"]["BASELINE"]["count"] == 25
    assert summary["cohorts"]["EVIDENCE_GATE"]["count"] == 25
    assert summary["readiness"] == "READY_FOR_HUMAN_EFFECTIVENESS_ADJUDICATION"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"
    assert summary["willingness_to_pay"] == "NOT_ESTABLISHED"
    assert summary["pmf"] == "NOT_ESTABLISHED"
    assert summary["automatic_superiority_claim"] is False
    assert summary["cohorts"]["EVIDENCE_GATE"]["sums"]["false_pass_caught"] == 2


def test_replay_measurements_never_unlock_effectiveness_readiness(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    for i in range(60):
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"R-{i}",
                cohort="EVIDENCE_GATE",
                measurement_mode="REPLAY",
                review_minutes=1,
            )
        )
    summary = recorder.summarize()

    assert summary["measurement_count"] == 60
    assert summary["prospective_measurement_count"] == 0
    assert summary["replay_measurement_count"] == 60
    assert summary["readiness_basis"] == "PROSPECTIVE_ONLY"
    assert summary["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"
    assert summary["automatic_superiority_claim"] is False


def test_replay_and_prospective_are_reported_separately(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    recorder.record(
        DogfoodMeasurementV0(
            task_id="P-1",
            cohort="EVIDENCE_GATE",
            measurement_mode="PROSPECTIVE",
            false_pass_caught=1,
        )
    )
    recorder.record(
        DogfoodMeasurementV0(
            task_id="R-1",
            cohort="EVIDENCE_GATE",
            measurement_mode="REPLAY",
            false_pass_caught=1,
        )
    )
    summary = recorder.summarize()

    assert summary["measurement_count"] == 2
    assert summary["prospective_measurement_count"] == 1
    assert summary["replay_measurement_count"] == 1
    assert summary["cohorts"]["EVIDENCE_GATE"]["count"] == 1
    assert summary["cohorts"]["EVIDENCE_GATE"]["sums"]["false_pass_caught"] == 1
    assert summary["replay"]["count"] == 1
    assert summary["replay"]["sums"]["false_pass_caught"] == 1


def test_measurement_rejects_unknown_mode(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="measurement_mode"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="T",
                cohort="EVIDENCE_GATE",
                measurement_mode="RETRO_GUESS",
            )
        )


def test_unmeasured_metrics_stay_unknown_not_zero(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    recorder = MeasurementRecorder(ledger)
    recorder.record(
        DogfoodMeasurementV0(
            task_id="U-1",
            cohort="EVIDENCE_GATE",
        )
    )
    event = ledger.events(task_id="U-1")[-1]
    summary = recorder.summarize()
    cohort = summary["cohorts"]["EVIDENCE_GATE"]

    assert event["payload"]["review_minutes"] is None
    assert event["payload"]["worker_cost_usd"] is None
    assert event["payload"]["false_pass_caught"] is None
    assert cohort["means"]["review_minutes"] is None
    assert cohort["sums"]["false_pass_caught"] is None
    assert cohort["measurement_coverage"]["observed_count"]["review_minutes"] == 0
    assert cohort["measurement_coverage"]["unknown_count"]["review_minutes"] == 1


def test_explicit_zero_is_observed_fact_not_unknown(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    recorder.record(
        DogfoodMeasurementV0(
            task_id="Z-1",
            cohort="EVIDENCE_GATE",
            false_pass_caught=0,
            review_minutes=0,
            task_to_validated_candidate_seconds=0,
            worker_cost_usd=0,
            evidence_reconstruction_seconds=0,
        )
    )
    summary = recorder.summarize()
    cohort = summary["cohorts"]["EVIDENCE_GATE"]

    assert cohort["sums"]["false_pass_caught"] == 0
    assert cohort["means"]["review_minutes"] == 0.0
    assert cohort["measurement_coverage"]["observed_count"]["review_minutes"] == 1
    assert cohort["measurement_coverage"]["unknown_count"]["review_minutes"] == 0


def test_balanced_50_with_unknown_core_metrics_is_not_ready(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    for i in range(25):
        task_id = f"BU-{i}"
        recorder.record(
            DogfoodMeasurementV0(
                task_id=task_id,
                cohort="BASELINE",
                review_minutes=10,
                metric_provenance=_observed_provenance(review_minutes=10),
                capture_context=_capture_context(task_id),
            )
        )
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"EU-{i}",
                cohort="EVIDENCE_GATE",
                review_minutes=5,
            )
        )
    summary = recorder.summarize()

    assert summary["prospective_measurement_count"] == 50
    assert summary["readiness"] == "MEASUREMENT_COMPLETENESS_NOT_ESTABLISHED"
    coverage = summary["prospective_measurement_coverage"]
    assert coverage["observed_count"]["review_minutes"] == 50
    assert coverage["unknown_count"]["worker_cost_usd"] == 50
    assert coverage["unknown_count"]["task_to_validated_candidate_seconds"] == 50
    assert summary["effectiveness"] == "NOT_ESTABLISHED"


def test_none_or_non_negative_numeric_validation(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    recorder.record(
        DogfoodMeasurementV0(
            task_id="N-1",
            cohort="EVIDENCE_GATE",
            review_minutes=None,
            false_pass_caught=None,
        )
    )
    with pytest.raises(MeasurementError, match="worker_cost_usd"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="N-2",
                cohort="EVIDENCE_GATE",
                worker_cost_usd=-0.01,
            )
        )

def test_metric_provenance_materializes_state_without_inventing_source(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    recorder = MeasurementRecorder(ledger)
    recorder.record(
        DogfoodMeasurementV0(
            task_id="PROV-1",
            cohort="EVIDENCE_GATE",
            review_minutes=0,
            worker_cost_usd=None,
        )
    )
    payload = ledger.events(task_id="PROV-1")[-1]["payload"]
    observed = payload["metric_provenance"]["review_minutes"]
    unknown = payload["metric_provenance"]["worker_cost_usd"]

    assert observed["state"] == "OBSERVED"
    assert observed["value"] == 0
    assert observed["capture_source"] == "NOT_ESTABLISHED"
    assert unknown["state"] == "UNKNOWN"
    assert unknown["value"] is None


def test_explicit_observed_provenance_requires_capture_fields(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="capture_source"):
        recorder.record(            DogfoodMeasurementV0(
                task_id="PROV-2",
                cohort="EVIDENCE_GATE",
                review_minutes=3,
                metric_provenance={
                    "review_minutes": MetricProvenanceV0(
                        state="OBSERVED",
                        value=3,
                    )
                },
            )
        )


def test_balanced_50_observed_values_without_capture_provenance_is_not_ready(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    for i in range(25):
        task_id = f"B-P-{i}"
        baseline_values = {
            "review_minutes": 1,
            "task_to_validated_candidate_seconds": 0,
            "worker_cost_usd": 0,
            "evidence_reconstruction_seconds": 0,
        }
        recorder.record(
            DogfoodMeasurementV0(
                task_id=task_id,
                cohort="BASELINE",
                **baseline_values,
                metric_provenance=_observed_provenance(**baseline_values),
                capture_context=_capture_context(task_id),
            )
        )
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"E-P-{i}",
                cohort="EVIDENCE_GATE",
                review_minutes=1,
                task_to_validated_candidate_seconds=0,
                worker_cost_usd=0,
                evidence_reconstruction_seconds=0,
            )
        )
    summary = recorder.summarize()
    assert summary["readiness"] == "MEASUREMENT_PROVENANCE_NOT_ESTABLISHED"
    assert summary["prospective_provenance_coverage"]["incomplete_count"]["review_minutes"] == 25

def test_baseline_requires_capture_context(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="BASELINE capture_context required"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="BASE-NO-CONTEXT",
                cohort="BASELINE",
            )
        )


def test_baseline_observed_zero_requires_explicit_provenance(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="requires explicit provenance"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="BASE-ZERO-BAD",
                cohort="BASELINE",
                false_pass_caught=0,
                capture_context=_capture_context("BASE-ZERO-BAD"),
            )
        )
    recorder.record(
        DogfoodMeasurementV0(
            task_id="BASE-ZERO-GOOD",
            cohort="BASELINE",
            false_pass_caught=0,
            metric_provenance=_observed_provenance(false_pass_caught=0),
            capture_context=_capture_context("BASE-ZERO-GOOD"),
        )
    )
    summary = recorder.summarize()
    baseline = summary["cohorts"]["BASELINE"]
    assert baseline["sums"]["false_pass_caught"] == 0
    assert baseline["measurement_coverage"]["observed_count"]["false_pass_caught"] == 1


def test_posthoc_reconstruction_cannot_be_prospective(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    with pytest.raises(MeasurementError, match="prospective measurement requires"):
        recorder.record(
            DogfoodMeasurementV0(
                task_id="BASE-RETRO-BAD",
                cohort="BASELINE",
                measurement_mode="PROSPECTIVE",
                capture_context=_capture_context(
                    "BASE-RETRO-BAD",
                    capture_basis="POST_HOC_RECONSTRUCTION",
                ),
            )
        )
    recorder.record(
        DogfoodMeasurementV0(
            task_id="BASE-RETRO-OK",
            cohort="BASELINE",
            measurement_mode="REPLAY",
            capture_context=_capture_context(
                "BASE-RETRO-OK",
                capture_basis="POST_HOC_RECONSTRUCTION",
            ),
        )
    )
    summary = recorder.summarize()
    assert summary["cohort_capture_protocol"]["BASELINE"]["prospective_count"] == 0
    assert summary["cohort_capture_protocol"]["BASELINE"]["replay_count"] == 1


def test_zero_baseline_keeps_comparison_not_established(tmp_path: Path):
    recorder = MeasurementRecorder(EventLedger(tmp_path / "ledger.sqlite3"))
    recorder.record(
        DogfoodMeasurementV0(
            task_id="EG-COMP-1",
            cohort="EVIDENCE_GATE",
            **_complete_capture("EG-COMP-1"),
        )
    )
    summary = recorder.summarize()
    assert summary["cohort_capture_protocol"]["BASELINE"]["prospective_count"] == 0
    assert summary["comparison_readiness"] == "BASELINE_SAMPLE_NOT_ESTABLISHED"
    assert summary["comparability"] == "NOT_ESTABLISHED"
    assert summary["effectiveness"] == "NOT_ESTABLISHED"
    assert summary["automatic_superiority_claim"] is False
