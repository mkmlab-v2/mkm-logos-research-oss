from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.measurement import (  # noqa: E402
    DogfoodMeasurementV0,
    MeasurementError,
    MeasurementRecorder,
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
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"B-{i}",
                cohort="BASELINE",
                wrong_repo_worktree_incidents=1 if i < 3 else 0,
                review_minutes=20,
                worker_cost_usd=2,
                builder_pass_validator_fail=1 if i < 4 else 0,
            )
        )
    for i in range(25):
        recorder.record(
            DogfoodMeasurementV0(
                task_id=f"E-{i}",
                cohort="EVIDENCE_GATE",
                wrong_repo_worktree_incidents=0,
                review_minutes=10,
                worker_cost_usd=2.5,
                builder_pass_validator_fail=1 if i < 2 else 0,
                false_pass_caught=1 if i < 2 else 0,
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
