from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.evidence import EvidenceEngine  # noqa: E402
from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.models import (  # noqa: E402
    AuthorityContract,
    EvidenceFreshness,
    EvidenceOutcome,
    GateDecision,
    TaskContract,
    TaskState,
    WorkerResult,
)
from mkm_orchestrator_v0.orchestrator import MKMOrchestrator, OrchestratorError  # noqa: E402
from mkm_orchestrator_v0.workspace import WorktreeManager  # noqa: E402
from mkm_orchestrator_v0.status import StatusBoard  # noqa: E402


def _git(repo: Path, *args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "MKM Fixture")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_app.py").write_text(
        "def test_value():\n    assert 1 == 1\n", encoding="utf-8"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, head


def _task(
    repo: Path,
    head: str,
    *,
    task_id: str = "TASK-001",
    mutation_authorized: bool = True,
    allowed_paths: tuple[str, ...] = ("app.py", "tests"),
) -> TaskContract:
    return TaskContract(
        task_id=task_id,
        objective="Bounded synthetic task",
        authority=AuthorityContract(
            repository_id="fixture-repo",
            repository_path=str(repo),
            base_revision=head,
            source_kind="AUTHORITATIVE",
            mutation_authorized=mutation_authorized,
        ),
        allowed_paths=allowed_paths,
        required_suites=("suite-a",),
        auto_next=False,
    )


def _orchestrator(tmp_path: Path):
    ledger = EventLedger(tmp_path / "state" / "ledger.sqlite3")
    worktrees = WorktreeManager(tmp_path / "worktrees")
    return ledger, MKMOrchestrator(ledger=ledger, worktrees=worktrees)


def test_ledger_is_hash_chained_and_append_only(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    one = ledger.append("A", {"x": 1}, task_id="T")
    two = ledger.append("B", {"y": 2}, task_id="T")
    assert two["prev_hash"] == one["event_hash"]
    assert ledger.verify_chain()["valid"] is True

    con = sqlite3.connect(ledger.path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE events SET event_type='X' WHERE seq=1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM events WHERE seq=1")
    con.close()


def test_one_task_gets_one_deterministic_worktree_binding(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    ledger, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task, create=True)

    assert Path(binding.worktree_path).is_dir()
    assert binding.base_revision == head
    assert _git(Path(binding.worktree_path), "rev-parse", "HEAD").stdout.strip() == head
    assert binding.branch_name.startswith("mkm/task-001-")
    events = ledger.events(task_id=task.task_id)
    assert [e["event_type"] for e in events] == ["TASK_CREATED", "WORKSPACE_BOUND"]


def test_duplicate_task_id_is_rejected(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    with pytest.raises(OrchestratorError, match="already exists"):
        orch.create_task(task)


def test_workspace_creation_requires_mutation_authority(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head, mutation_authorized=False)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    with pytest.raises(OrchestratorError, match="does not authorize"):
        orch.bind_workspace(task, create=True)


@dataclass
class FakeWorker:
    worker_id: str
    changed_files: tuple[str, ...]
    subject_digest: str = "a" * 64

    def run(self, task, workspace):
        return WorkerResult(
            worker_id=self.worker_id,
            task_id=task.task_id,
            status="PASS",
            subject_digest=self.subject_digest,
            changed_files=self.changed_files,
            summary="fixture worker claim",
            metadata={"claim": "not evidence"},
        )


def test_worker_claim_does_not_promote_without_evidence(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    orch.dispatch(task, binding, FakeWorker("builder-1", ("app.py",)))
    gate = orch.evaluate(task.task_id)

    assert gate.task_state == TaskState.HOLD
    assert gate.decision == GateDecision.HOLD
    assert gate.reason == "NO_EVIDENCE"
    assert gate.merge_authorization == "NO"


def test_changed_file_outside_contract_is_policy_violation(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head, allowed_paths=("app.py",))
    ledger, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task)

    with pytest.raises(OrchestratorError, match="outside allowed_paths"):
        orch.dispatch(task, binding, FakeWorker("builder-1", ("secrets.txt",)))

    gate = orch.evaluate(task.task_id)
    assert gate.task_state == TaskState.HOLD
    assert gate.reason == "POLICY_VIOLATION_REQUIRES_ADJUDICATION"
    assert any(e["event_type"] == "POLICY_VIOLATION" for e in ledger.events(task_id=task.task_id))


def test_builder_pass_alone_is_not_candidate(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    result = orch.dispatch(task, binding, FakeWorker("builder-1", ("app.py",)))
    ev = orch.record_builder_evidence(
        result,
        suite_id="suite-a",
        suite_digest="1" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "1 passed"},
    )
    gate = orch.evaluate(task.task_id)

    assert ev.freshness == EvidenceFreshness.BUILDER_SELF_REPORT
    assert gate.task_state == TaskState.HOLD
    assert gate.evidence_ceiling == "NOT_ADJUDICATED"


def test_independent_fresh_pass_creates_candidate_but_not_authorization(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    result = orch.dispatch(task, binding, FakeWorker("builder-1", ("app.py",), "b" * 64))

    orch.record_builder_evidence(
        result,
        suite_id="builder-suite",
        suite_digest="1" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "builder pass"},
    )
    validator = orch.record_validator_evidence(
        task_id=task.task_id,
        validator_id="validator-1",
        suite_id="independent-suite",
        suite_digest="2" * 64,
        subject_digest=result.subject_digest,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "independent pass"},
    )
    gate = orch.evaluate(task.task_id)

    assert validator.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    assert gate.task_state == TaskState.CANDIDATE
    assert gate.decision == GateDecision.HUMAN_GATE
    assert gate.merge_authorization == "NO"
    assert gate.deployment_authorization == "NO"
    assert gate.send_gate == "HOLD"


def test_fresh_fail_is_sealed_and_patch_confirmation_cannot_erase_it(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task)

    fail = orch.record_validator_evidence(
        task_id=task.task_id,
        validator_id="validator-1",
        suite_id="semantic-suite",
        suite_digest="3" * 64,
        subject_digest="old-subject",
        outcome=EvidenceOutcome.FAIL,
        detail={"failure": "semantic mismatch"},
    )
    assert fail.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    first_gate = orch.evaluate(task.task_id)
    assert first_gate.task_state == TaskState.FAIL
    assert first_gate.reason == "SEALED_INDEPENDENT_FRESH_FAIL"

    confirmation = orch.record_validator_evidence(
        task_id=task.task_id,
        validator_id="validator-1",
        suite_id="semantic-suite",
        suite_digest="3" * 64,
        subject_digest="patched-subject",
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "same suite now passes"},
    )
    assert confirmation.freshness == EvidenceFreshness.PATCH_CONFIRMATION

    second_gate = orch.evaluate(task.task_id)
    assert second_gate.task_state == TaskState.FAIL
    assert second_gate.reason == "SEALED_INDEPENDENT_FRESH_FAIL"
    assert second_gate.evidence_ceiling == "FAIL"


def test_repeat_same_validator_observation_is_not_fresh(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    engine = EvidenceEngine(ledger)
    first = engine.record(
        task_id="T",
        actor_id="validator-1",
        actor_role="VALIDATOR",
        suite_id="suite-x",
        suite_digest="4" * 64,
        subject_digest="subject",
        outcome=EvidenceOutcome.PASS,
        detail={"run": 1},
    )
    second = engine.record(
        task_id="T",
        actor_id="validator-1",
        actor_role="VALIDATOR",
        suite_id="suite-x",
        suite_digest="4" * 64,
        subject_digest="subject",
        outcome=EvidenceOutcome.PASS,
        detail={"run": 2},
    )
    assert first.freshness == EvidenceFreshness.INDEPENDENT_FRESH
    assert second.freshness == EvidenceFreshness.REPEAT_OBSERVATION


def test_task_workspace_mismatch_is_rejected(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task_a = _task(repo, head, task_id="TASK-A")
    task_b = _task(repo, head, task_id="TASK-B")
    _, orch = _orchestrator(tmp_path)
    orch.create_task(task_a)
    binding = orch.bind_workspace(task_a)

    with pytest.raises(OrchestratorError, match="workspace/task mismatch"):
        orch.dispatch(task_b, binding, FakeWorker("builder-1", ("app.py",)))


def test_status_board_is_derived_and_keeps_authorization_closed(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    ledger, orch = _orchestrator(tmp_path)
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    result = orch.dispatch(task, binding, FakeWorker("builder-1", ("app.py",), "c" * 64))
    orch.record_builder_evidence(
        result,
        suite_id="builder-suite",
        suite_digest="5" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "builder pass"},
    )
    orch.record_validator_evidence(
        task_id=task.task_id,
        validator_id="validator-1",
        suite_id="independent-suite",
        suite_digest="6" * 64,
        subject_digest=result.subject_digest,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "independent pass"},
    )
    orch.evaluate(task.task_id)

    before = ledger.verify_chain()
    board = StatusBoard(ledger).build()
    after = ledger.verify_chain()

    assert board["derived_view"] is True
    assert board["authoritative_source"] == "APPEND_ONLY_EVENT_LEDGER"
    assert board["ledger"]["integrity"]["valid"] is True
    assert board["tasks"][0]["current_state"] == "CANDIDATE"
    assert board["tasks"][0]["gate_decision"] == "HUMAN_GATE"
    assert board["tasks"][0]["merge_authorization"] == "NO"
    assert board["tasks"][0]["deployment_authorization"] == "NO"
    assert board["global_boundaries"]["auto_merge"] == "NO"
    assert board["global_boundaries"]["worker_claim_is_evidence"] is False
    assert before == after


def test_status_export_does_not_mutate_ledger(tmp_path: Path):
    ledger = EventLedger(tmp_path / "ledger.sqlite3")
    ledger.append("TASK_CREATED", {"objective": "fixture"}, task_id="T")
    before = ledger.verify_chain()
    target = tmp_path / "CURRENT_STATUS.json"
    StatusBoard(ledger).export(target)
    after = ledger.verify_chain()

    payload = __import__("json").loads(target.read_text(encoding="utf-8"))
    assert payload["derived_view"] is True
    assert payload["task_count"] == 1
    task = payload["tasks"][0]
    assert task["authority"]["state"] == "UNKNOWN"
    assert task["authority"]["reason"] == "MISSING_TASK_CREATED_AUTHORITY"
    assert task["data_quality"]["state"] == "UNKNOWN"
    assert task["data_quality"]["missing_fields"] == ["authority"]
    assert before == after
