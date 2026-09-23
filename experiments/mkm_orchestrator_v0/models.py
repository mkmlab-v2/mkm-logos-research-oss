from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EpistemicState(str, Enum):
    FACT = "FACT"
    SUPPORTED = "SUPPORTED"
    INFERENCE = "INFERENCE"
    PLAUSIBLE = "PLAUSIBLE"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    NOT_ADJUDICATED = "NOT_ADJUDICATED"
    FAIL = "FAIL"


class TaskState(str, Enum):
    CREATED = "CREATED"
    WORKSPACE_BOUND = "WORKSPACE_BOUND"
    RUNNING = "RUNNING"
    BUILT = "BUILT"
    VALIDATING = "VALIDATING"
    CANDIDATE = "CANDIDATE"
    HOLD = "HOLD"
    FAIL = "FAIL"


class EvidenceOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class EvidenceFreshness(str, Enum):
    BUILDER_SELF_REPORT = "BUILDER_SELF_REPORT"
    INDEPENDENT_FRESH = "INDEPENDENT_FRESH"
    PATCH_CONFIRMATION = "PATCH_CONFIRMATION"
    REPEAT_OBSERVATION = "REPEAT_OBSERVATION"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class GateDecision(str, Enum):
    HOLD = "HOLD"
    HUMAN_GATE = "HUMAN_GATE"
    DENY = "DENY"


@dataclass(frozen=True)
class AuthorityContract:
    repository_id: str
    repository_path: str
    base_revision: str
    source_kind: str = "AUTHORITATIVE"
    mutation_authorized: bool = False

    def validate(self) -> None:
        if not self.repository_id.strip():
            raise ValueError("repository_id required")
        if not self.repository_path.strip():
            raise ValueError("repository_path required")
        if not self.base_revision.strip():
            raise ValueError("base_revision required")
        if self.source_kind not in {"AUTHORITATIVE", "WORKING_MIRROR"}:
            raise ValueError("source_kind must be AUTHORITATIVE or WORKING_MIRROR")


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    objective: str
    authority: AuthorityContract
    allowed_paths: tuple[str, ...] = ()
    required_suites: tuple[str, ...] = ()
    auto_next: bool = False

    def validate(self) -> None:
        if not self.task_id or any(ch.isspace() for ch in self.task_id):
            raise ValueError("task_id must be nonblank and contain no whitespace")
        if not self.objective.strip():
            raise ValueError("objective required")
        self.authority.validate()


@dataclass(frozen=True)
class WorkspaceBinding:
    task_id: str
    branch_name: str
    worktree_path: str
    base_revision: str
    repository_path: str


@dataclass(frozen=True)
class WorkerResult:
    worker_id: str
    task_id: str
    status: str
    subject_digest: str
    changed_files: tuple[str, ...] = ()
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    task_id: str
    actor_id: str
    actor_role: str
    suite_id: str
    suite_digest: str
    subject_digest: str
    outcome: EvidenceOutcome
    freshness: EvidenceFreshness
    detail_digest: str
    created_at: str


@dataclass(frozen=True)
class GateEvaluation:
    task_id: str
    task_state: TaskState
    decision: GateDecision
    reason: str
    evidence_ceiling: str
    merge_authorization: str = "NO"
    deployment_authorization: str = "NO"
    send_gate: str = "HOLD"
