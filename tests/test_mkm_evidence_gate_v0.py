from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from mkm_orchestrator_v0.authority import (  # noqa: E402
    AuthorityResolver,
    SourceClass,
    write_role_marker,
)
from mkm_orchestrator_v0.ledger import EventLedger  # noqa: E402
from mkm_orchestrator_v0.models import (  # noqa: E402
    AuthorityContract,
    EvidenceOutcome,
    TaskContract,
    WorkerResult,
)
from mkm_orchestrator_v0.orchestrator import MKMOrchestrator  # noqa: E402
from mkm_orchestrator_v0.receipt import EvidenceReceiptBuilder, observe_workspace  # noqa: E402
from mkm_orchestrator_v0.workspace import WorktreeManager  # noqa: E402


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


def _repo(tmp_path: Path, name: str = "source") -> tuple[Path, str]:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "MKM Evidence Fixture")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, head


def _authority(repo: Path, head: str, source_kind: str = "AUTHORITATIVE"):
    return AuthorityContract(
        repository_id="fixture-repo",
        repository_path=str(repo),
        base_revision=head,
        source_kind=source_kind,
        mutation_authorized=True,
    )


def _task(repo: Path, head: str) -> TaskContract:
    return TaskContract(
        task_id="EVIDENCE-001",
        objective="Evidence gate fixture",
        authority=_authority(repo, head),
        allowed_paths=("app.py",),
        required_suites=("suite-a",),
    )


def test_authority_exact_declared_repo_is_authoritative(tmp_path: Path):
    repo, head = _repo(tmp_path)
    result = AuthorityResolver(_authority(repo, head)).resolve(repo)
    assert result["source_class"] == SourceClass.AUTHORITATIVE
    assert result["reason"] == "EXACT_DECLARED_REPOSITORY_PATH"
    assert result["promotion_authorized"] is False


def test_exact_declared_working_mirror_stays_working_mirror(tmp_path: Path):
    repo, head = _repo(tmp_path)
    result = AuthorityResolver(
        _authority(repo, head, source_kind="WORKING_MIRROR")
    ).resolve(repo)
    assert result["source_class"] == SourceClass.WORKING_MIRROR
    assert result["promotion_authorized"] is False


def test_exact_task_binding_is_task_worktree(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    manager = WorktreeManager(tmp_path / "worktrees")
    binding = manager.plan(task)
    manager.create(binding)

    result = AuthorityResolver(task.authority).resolve(
        binding.worktree_path,
        task_binding=binding,
    )
    assert result["source_class"] == SourceClass.TASK_WORKTREE
    assert result["reason"] == "EXACT_TASK_BINDING_AND_SHARED_GIT_COMMON_DIR"


def test_unbound_linked_worktree_is_unknown(tmp_path: Path):
    repo, head = _repo(tmp_path)
    other = tmp_path / "unbound"
    _git(repo, "worktree", "add", "-b", "fixture-unbound", str(other), head)

    result = AuthorityResolver(_authority(repo, head)).resolve(other)
    assert result["source_class"] == SourceClass.UNKNOWN
    assert result["reason"] == "UNBOUND_LINKED_WORKTREE"


def test_same_remote_separate_clone_without_marker_is_unknown(tmp_path: Path):
    repo, head = _repo(tmp_path)
    remote = "https://example.invalid/mkm-fixture.git"
    _git(repo, "remote", "add", "origin", remote)

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", str(repo), str(clone)],
        check=True,
        text=True,
        capture_output=True,
    )
    _git(clone, "remote", "set-url", "origin", remote)

    result = AuthorityResolver(_authority(repo, head)).resolve(clone)
    assert result["source_class"] == SourceClass.UNKNOWN
    assert result["reason"] == "SAME_REMOTE_SEPARATE_CLONE_WITHOUT_ROLE_MARKER"


def test_explicit_matching_validation_clone_marker_is_accepted(tmp_path: Path):
    repo, head = _repo(tmp_path)
    remote = "https://example.invalid/mkm-fixture.git"
    _git(repo, "remote", "add", "origin", remote)
    clone = tmp_path / "validation"
    subprocess.run(
        ["git", "clone", str(repo), str(clone)],
        check=True,
        text=True,
        capture_output=True,
    )
    _git(clone, "remote", "set-url", "origin", remote)
    write_role_marker(
        clone,
        role=SourceClass.VALIDATION_CLONE,
        authority_repository_id="fixture-repo",
        authority_base_revision=head,
    )

    result = AuthorityResolver(_authority(repo, head)).resolve(clone)
    assert result["source_class"] == SourceClass.VALIDATION_CLONE
    assert result["reason"] == "EXPLICIT_ROLE_MARKER_MATCH"


def test_conflicting_role_marker_fails_closed(tmp_path: Path):
    repo, head = _repo(tmp_path)
    archive = tmp_path / "archive"
    archive.mkdir()
    write_role_marker(
        archive,
        role=SourceClass.ARCHIVE,
        authority_repository_id="other-repo",
        authority_base_revision=head,
    )

    result = AuthorityResolver(_authority(repo, head)).resolve(archive)
    assert result["source_class"] == SourceClass.CONFLICT
    assert result["reason"] == "ROLE_MARKER_REPOSITORY_CONFLICT"


class ExactWorker:
    worker_id = "builder-fixture"

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
            summary="fixture exact worker",
            metadata={"backend": "fixture", "result_revision": observed["result_revision"]},
        )


def _candidate_task(tmp_path: Path):
    repo, head = _repo(tmp_path)
    task = _task(repo, head)
    ledger = EventLedger(tmp_path / "state" / "ledger.sqlite3")
    orch = MKMOrchestrator(
        ledger=ledger,
        worktrees=WorktreeManager(tmp_path / "worktrees"),
    )
    orch.create_task(task)
    binding = orch.bind_workspace(task)
    result = orch.dispatch(task, binding, ExactWorker())
    orch.record_builder_evidence(
        result,
        suite_id="builder-suite",
        suite_digest="1" * 64,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "builder pass"},
    )
    orch.record_validator_evidence(
        task_id=task.task_id,
        validator_id="validator-fixture",
        suite_id="validator-suite",
        suite_digest="2" * 64,
        subject_digest=result.subject_digest,
        outcome=EvidenceOutcome.PASS,
        detail={"tests": "validator pass"},
    )
    orch.evaluate(task.task_id)
    return ledger, task, binding, result


def test_receipt_reobserves_workspace_and_matches_worker_claim(tmp_path: Path):
    ledger, task, _binding, result = _candidate_task(tmp_path)
    receipt = EvidenceReceiptBuilder(ledger).build(task.task_id)

    assert receipt["schema"] == "mkm_evidence_receipt_v0"
    assert receipt["observed_result"]["state"] == "FACT"
    assert receipt["observed_result"]["changed_files"] == ["app.py"]
    assert len(receipt["observed_result"]["diff_sha256"]) == 64
    assert receipt["worker_claim"]["state"] == "WORKER_CLAIM_ONLY"
    assert receipt["worker_claim_consistency"]["result"] == "MATCH"
    assert receipt["observed_result"]["subject_digest"] == result.subject_digest


def test_receipt_candidate_still_has_no_merge_deploy_or_send_authority(tmp_path: Path):
    ledger, task, _binding, _result = _candidate_task(tmp_path)
    receipt = EvidenceReceiptBuilder(ledger).build(task.task_id)

    assert receipt["evidence_ceiling"] == "BOUNDED_MERGE_CANDIDATE"
    assert receipt["authorization"]["gate_decision"] == "HUMAN_GATE"
    assert receipt["authorization"]["merge"] == "NO"
    assert receipt["authorization"]["deployment"] == "NO"
    assert receipt["authorization"]["send"] == "HOLD"


def test_receipt_detects_worker_claim_drift_after_workspace_changes(tmp_path: Path):
    ledger, task, binding, _result = _candidate_task(tmp_path)
    root = Path(binding.worktree_path)
    (root / "app.py").write_text("VALUE = 999\n", encoding="utf-8")

    receipt = EvidenceReceiptBuilder(ledger).build(task.task_id)
    assert receipt["worker_claim_consistency"]["result"] == "MISMATCH"
    assert receipt["worker_claim_consistency"]["subject_digest_match"] is False


def test_issuing_receipt_appends_only_receipt_metadata_and_covers_prior_head(tmp_path: Path):
    ledger, task, _binding, _result = _candidate_task(tmp_path)
    before = ledger.verify_chain()
    receipt = EvidenceReceiptBuilder(ledger).issue(task.task_id)
    after = ledger.verify_chain()
    events = ledger.events(task_id=task.task_id)

    assert before["valid"] is True
    assert after["valid"] is True
    assert after["event_count"] == before["event_count"] + 1
    assert receipt["ledger"]["covered_head_hash"] == before["head_hash"]
    assert events[-1]["event_type"] == "EVIDENCE_RECEIPT_ISSUED"
    assert events[-1]["payload"]["receipt_sha256"] == receipt["receipt_sha256"]
