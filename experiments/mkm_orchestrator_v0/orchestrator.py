from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .evidence import EvidenceEngine
from .ledger import EventLedger
from .models import EvidenceOutcome, TaskContract, WorkerResult
from .worker import WorkerAdapter
from .workspace import WorktreeManager


class OrchestratorError(RuntimeError):
    pass


class MKMOrchestrator:
    """Bounded V0 orchestrator.

    V0 can create task/worktree bindings and record worker/evidence events.
    It cannot merge, push, deploy, delete worktrees, or promote automatically.
    """

    def __init__(
        self,
        *,
        ledger: EventLedger,
        worktrees: WorktreeManager,
    ):
        self.ledger = ledger
        self.worktrees = worktrees
        self.evidence = EvidenceEngine(ledger)

    def create_task(self, task: TaskContract) -> dict[str, Any]:
        task.validate()
        existing = [
            e for e in self.ledger.events(task_id=task.task_id)
            if e["event_type"] == "TASK_CREATED"
        ]
        if existing:
            raise OrchestratorError("task_id already exists")
        event = self.ledger.append(
            "TASK_CREATED",
            {
                "objective": task.objective,
                "authority": asdict(task.authority),
                "allowed_paths": list(task.allowed_paths),
                "required_suites": list(task.required_suites),
                "auto_next": task.auto_next,
            },
            task_id=task.task_id,
        )
        return event

    def bind_workspace(self, task: TaskContract, *, create: bool = True):
        if not self.ledger.events(task_id=task.task_id):
            raise OrchestratorError("task must be created before workspace binding")
        if create and not task.authority.mutation_authorized:
            raise OrchestratorError("authority does not authorize workspace mutation")
        binding = self.worktrees.plan(task)
        if create:
            self.worktrees.create(binding)
        self.ledger.append(
            "WORKSPACE_BOUND",
            asdict(binding),
            task_id=task.task_id,
        )
        return binding

    def dispatch(
        self,
        task: TaskContract,
        binding,
        worker: WorkerAdapter,
    ) -> WorkerResult:
        if binding.task_id != task.task_id:
            raise OrchestratorError("workspace/task mismatch")
        self.ledger.append(
            "WORKER_STARTED",
            {
                "worker_id": worker.worker_id,
                "worktree_path": binding.worktree_path,
                "base_revision": binding.base_revision,
            },
            task_id=task.task_id,
        )
        result = worker.run(task, binding)
        if result.task_id != task.task_id:
            raise OrchestratorError("worker returned wrong task_id")
        violations = self._changed_path_violations(task, result.changed_files)
        if violations:
            self.ledger.append(
                "POLICY_VIOLATION",
                {
                    "kind": "CHANGED_PATH_OUTSIDE_TASK_CONTRACT",
                    "worker_id": result.worker_id,
                    "violations": violations,
                },
                task_id=task.task_id,
            )
            raise OrchestratorError(
                "worker reported changes outside allowed_paths: " + ",".join(violations)
            )
        self.ledger.append(
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
        return result

    def record_builder_evidence(
        self,
        result: WorkerResult,
        *,
        suite_id: str,
        suite_digest: str,
        outcome: EvidenceOutcome,
        detail: dict[str, Any],
    ):
        return self.evidence.record(
            task_id=result.task_id,
            actor_id=result.worker_id,
            actor_role="BUILDER",
            suite_id=suite_id,
            suite_digest=suite_digest,
            subject_digest=result.subject_digest,
            outcome=outcome,
            detail=detail,
        )

    def record_validator_evidence(
        self,
        *,
        task_id: str,
        validator_id: str,
        suite_id: str,
        suite_digest: str,
        subject_digest: str,
        outcome: EvidenceOutcome,
        detail: dict[str, Any],
    ):
        return self.evidence.record(
            task_id=task_id,
            actor_id=validator_id,
            actor_role="VALIDATOR",
            suite_id=suite_id,
            suite_digest=suite_digest,
            subject_digest=subject_digest,
            outcome=outcome,
            detail=detail,
        )

    @staticmethod
    def _changed_path_violations(
        task: TaskContract,
        changed_files: tuple[str, ...],
    ) -> list[str]:
        if not changed_files:
            return []
        if not task.allowed_paths:
            return list(changed_files)

        normalized_allowed = [
            p.replace("\\", "/").strip("/")
            for p in task.allowed_paths
            if p.strip("/")
        ]
        violations = []
        for raw in changed_files:
            path = raw.replace("\\", "/").strip("/")
            if path.startswith("../") or path == "..":
                violations.append(raw)
                continue
            allowed = any(
                path == prefix or path.startswith(prefix + "/")
                for prefix in normalized_allowed
            )
            if not allowed:
                violations.append(raw)
        return violations

    def evaluate(self, task_id: str):
        if any(
            e["event_type"] == "POLICY_VIOLATION"
            for e in self.ledger.events(task_id=task_id)
        ):
            from .models import GateDecision, GateEvaluation, TaskState
            result = GateEvaluation(
                task_id=task_id,
                task_state=TaskState.HOLD,
                decision=GateDecision.HOLD,
                reason="POLICY_VIOLATION_REQUIRES_ADJUDICATION",
                evidence_ceiling="FAIL",
            )
            self.evidence._record_gate(result)
            return result
        return self.evidence.evaluate_gate(task_id)
