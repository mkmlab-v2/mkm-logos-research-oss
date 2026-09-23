from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.dogfood import DogfoodRunner, DogfoodRunnerError  # noqa: E402
from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.measurement import DogfoodMeasurementV0  # noqa: E402
from mkm_orchestrator_v0.models import (  # noqa: E402
    AuthorityContract,
    EvidenceOutcome,
    TaskContract,
    WorkerResult,
    WorkspaceBinding,
)
from mkm_orchestrator_v0.receipt import observe_workspace  # noqa: E402
from mkm_orchestrator_v0.shared_status import SharedStatusPublisher  # noqa: E402
from mkm_orchestrator_v0.validator import IndependentValidatorContract  # noqa: E402


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


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "MKM Dogfood Fixture")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo, _git(repo, "rev-parse", "HEAD").stdout.strip()


def _task(repo: Path, head: str, task_id: str = "DOG-001") -> TaskContract:
    return TaskContract(
        task_id=task_id,
        objective="Dogfood runner fixture",
        authority=AuthorityContract(
            repository_id="dogfood-fixture",
            repository_path=str(repo),
            base_revision=head,
            source_kind="AUTHORITATIVE",
            mutation_authorized=True,
        ),
        allowed_paths=("app.py",),
        required_suites=("validator-suite",),
        auto_next=False,
    )


def _runner(tmp_path: Path):
    ledger = EventLedger(tmp_path / "state" / "ledger.sqlite3")
    runner = DogfoodRunner(
        ledger=ledger,
        worktree_root=tmp_path / "worktrees",
        shared_status_dir=tmp_path / "shared",
    )
    return ledger, runner


class ExactWorker:
    worker_id = "builder-dogfood"

    def run(self, task, workspace):
        root = Path(workspace.worktree_path)
        (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        observed = observe_workspace(root)
        return WorkerResult(
            worker_id=self.worker_id,
            task_id=task.task_id,
            status="PASS",
            subject_digest=observed["subject_digest"],
            changed_files=tuple(observed["changed_files"]),
            summary="bounded dogfood fixture",
            metadata={"backend": "fixture"},
        )


def test_start_creates_task_worktree_and_shared_current_status(tmp_path: Path):
    repo, head = _repo(tmp_path)
    ledger, runner = _runner(tmp_path)
    started = runner.start(_task(repo, head))

    assert Path(started["workspace"]["worktree_path"]).is_dir()
    assert started["next_action"] == "WORKER_EXECUTION_EXTERNAL"
    assert started["merge_authorization"] == "NO"
    assert started["deployment_authorization"] == "NO"
    assert started["send_gate"] == "HOLD"

    verified = SharedStatusPublisher(ledger).verify(tmp_path / "shared")
    assert verified["state"] == "CURRENT"
    payload = json.loads((tmp_path / "shared" / "CURRENT_STATUS.json").read_text(encoding="utf-8"))
    assert payload["authoritative_source"] == "APPEND_ONLY_EVENT_LEDGER"
    assert payload["derived_view"] is True
    assert payload["global_boundaries"]["automatic_next_task"] == "NO"


def test_duplicate_start_is_rejected(tmp_path: Path):
    repo, head = _repo(tmp_path)
    _ledger, runner = _runner(tmp_path)
    task = _task(repo, head)
    runner.start(task)
    with pytest.raises((DogfoodRunnerError, Exception), match="already"):
        runner.start(task)


def test_finalize_without_evidence_stays_hold_and_records_measurement(tmp_path: Path):
    repo, head = _repo(tmp_path)
    ledger, runner = _runner(tmp_path)
    task = _task(repo, head)
    runner.start(task)

    result = runner.finalize(
        task.task_id,
        DogfoodMeasurementV0(
            task_id=task.task_id,
            cohort="EVIDENCE_GATE",
            review_minutes=3,
            human_interventions=1,
        ),
    )
    assert result["task_state"] == "HOLD"
    assert result["gate_decision"] == "HOLD"
    assert result["next_action"] == "HOLD"
    assert result["merge_authorization"] == "NO"
    assert result["deployment_authorization"] == "NO"
    assert result["send_gate"] == "HOLD"
    assert result["dogfood_summary"]["measurement_count"] == 1
    assert result["dogfood_summary"]["effectiveness"] == "NOT_ESTABLISHED"

    verified = SharedStatusPublisher(ledger).verify(tmp_path / "shared")
    assert verified["state"] == "CURRENT"


def test_candidate_finalize_requires_human_gate_and_never_auto_advances(tmp_path: Path):
    repo, head = _repo(tmp_path)
    ledger, runner = _runner(tmp_path)
    task = _task(repo, head)
    started = runner.start(task)
    binding = WorkspaceBinding(**started["workspace"])

    worker = ExactWorker()
    result = runner.orchestrator.dispatch(task, binding, worker)
    runner.orchestrator.record_builder_evidence(
        result,
        suite_id="builder-suite",
        suite_digest="a" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"claim": "builder pass"},
    )
    observed = observe_workspace(binding.worktree_path)
    validator = IndependentValidatorContract(ledger)
    validator.record_test_result(
        task_id=task.task_id,
        validator_id="validator-dogfood",
        suite_id="validator-suite",
        suite_digest="b" * 64,
        subject_digest=observed["subject_digest"],
        returncode=0,
        stdout_sha256="c" * 64,
        stderr_sha256="d" * 64,
        duration_ms=25,
    )

    finalized = runner.finalize(
        task.task_id,
        DogfoodMeasurementV0(
            task_id=task.task_id,
            cohort="EVIDENCE_GATE",
            false_pass_caught=0,
            review_minutes=4,
            task_to_validated_candidate_seconds=12,
            worker_cost_usd=0.25,
        ),
    )

    assert finalized["task_state"] == "CANDIDATE"
    assert finalized["gate_decision"] == "HUMAN_GATE"
    assert finalized["next_action"] == "HUMAN_GATE"
    assert finalized["merge_authorization"] == "NO"
    assert finalized["deployment_authorization"] == "NO"
    assert finalized["send_gate"] == "HOLD"

    payload = json.loads((tmp_path / "shared" / "CURRENT_STATUS.json").read_text(encoding="utf-8"))
    assert payload["dogfood"]["measurement_count"] == 1
    assert payload["dogfood"]["readiness"] == "INSUFFICIENT_DOGFOOD_SAMPLE_LT_50"
    assert task.task_id in payload["latest_receipts"]
    assert task.task_id in payload["finalized_tasks"]
    assert payload["finalized_tasks"][task.task_id]["next_action"] == "HUMAN_GATE"
    assert payload["global_boundaries"]["automatic_next_task"] == "NO"


def test_measurement_task_and_cohort_must_match_started_task(tmp_path: Path):
    repo, head = _repo(tmp_path)
    _ledger, runner = _runner(tmp_path)
    task = _task(repo, head)
    runner.start(task)

    with pytest.raises(DogfoodRunnerError, match="task_id mismatch"):
        runner.finalize(
            task.task_id,
            DogfoodMeasurementV0(
                task_id="OTHER",
                cohort="EVIDENCE_GATE",
            ),
        )

    with pytest.raises(DogfoodRunnerError, match="cohort mismatch"):
        runner.finalize(
            task.task_id,
            DogfoodMeasurementV0(
                task_id=task.task_id,
                cohort="BASELINE",
            ),
        )


def test_duplicate_finalize_is_rejected(tmp_path: Path):
    repo, head = _repo(tmp_path)
    _ledger, runner = _runner(tmp_path)
    task = _task(repo, head)
    runner.start(task)
    measurement = DogfoodMeasurementV0(
        task_id=task.task_id,
        cohort="EVIDENCE_GATE",
    )
    runner.finalize(task.task_id, measurement)
    with pytest.raises(DogfoodRunnerError, match="already finalized"):
        runner.finalize(task.task_id, measurement)


def test_shared_status_becomes_stale_when_ledger_advances(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    publisher = SharedStatusPublisher(ledger)
    publisher.publish(tmp_path / "shared")
    assert publisher.verify(tmp_path / "shared")["state"] == "CURRENT"

    ledger.append("FIXTURE_2", {"x": 2}, task_id="T")
    verified = publisher.verify(tmp_path / "shared")
    assert verified["state"] == "STALE"
    assert verified["reason"] == "LEDGER_ADVANCED_SINCE_PUBLICATION"
    assert verified["sha256_valid"] is True


def test_shared_status_tamper_is_detected(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    publisher = SharedStatusPublisher(ledger)
    publisher.publish(tmp_path / "shared")

    status_path = tmp_path / "shared" / "CURRENT_STATUS.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["global_boundaries"]["automatic_merge"] = "YES"
    status_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    verified = publisher.verify(tmp_path / "shared")
    assert verified["state"] == "INVALID"
    assert verified["reason"] == "STATUS_SHA256_MISMATCH"


def test_shared_status_seal_matches_published_bytes(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    ledger.append("FIXTURE", {"x": 1}, task_id="T")
    publisher = SharedStatusPublisher(ledger)
    published = publisher.publish(tmp_path / "shared")

    raw = (tmp_path / "shared" / "CURRENT_STATUS.json").read_bytes()
    seal = json.loads((tmp_path / "shared" / "CURRENT_STATUS.sha256.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == published["sha256"]
    assert seal["sha256"] == published["sha256"]
    assert seal["covered_head_hash"] == ledger.verify_chain()["head_hash"]
