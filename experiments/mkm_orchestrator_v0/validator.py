from __future__ import annotations

import hashlib
import re
from pathlib import Path
import subprocess
from typing import Any

from .evidence import EvidenceEngine
from .ledger import EventLedger
from .models import EvidenceOutcome
from .receipt import observe_workspace


class ValidationContractError(RuntimeError):
    pass


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=15,
        shell=False,
    )


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip("/")


class IndependentValidatorContract:
    """Accepts validator test artifacts only after structural re-observation.

    This class does not execute arbitrary validator commands. A validator adapter
    runs its own bounded suite and submits only digests/return code here.
    """

    def __init__(self, ledger: EventLedger):
        self.ledger = ledger
        self.evidence = EvidenceEngine(ledger)

    def record_test_result(
        self,
        *,
        task_id: str,
        validator_id: str,
        suite_id: str,
        suite_digest: str,
        subject_digest: str,
        returncode: int,
        stdout_sha256: str,
        stderr_sha256: str,
        duration_ms: int,
    ):
        task = self._task(task_id)
        workspace = self._workspace(task_id)
        builder = self._last_builder(task_id)

        if not validator_id.strip():
            return self._reject(task_id, "VALIDATOR_ID_REQUIRED")
        if builder and builder.get("worker_id") == validator_id:
            return self._reject(task_id, "BUILDER_VALIDATOR_IDENTITY_COLLISION")
        if not suite_id.strip():
            return self._reject(task_id, "SUITE_ID_REQUIRED")
        for name, value in {
            "suite_digest": suite_digest,
            "subject_digest": subject_digest,
            "stdout_sha256": stdout_sha256,
            "stderr_sha256": stderr_sha256,
        }.items():
            if not _SHA256.fullmatch(value):
                return self._reject(task_id, f"{name.upper()}_INVALID")
        if duration_ms < 0:
            return self._reject(task_id, "DURATION_INVALID")

        observed = observe_workspace(workspace["worktree_path"])
        if observed.get("state") != "FACT":
            return self._reject(task_id, "WORKSPACE_OBSERVATION_NOT_ESTABLISHED")
        if observed["subject_digest"] != subject_digest:
            return self._reject(task_id, "SUBJECT_DIGEST_DRIFT")

        base_revision = workspace.get("base_revision")
        if not base_revision:
            return self._reject(task_id, "BASE_REVISION_NOT_ESTABLISHED")
        root = Path(workspace["worktree_path"]).resolve()
        ancestor = _git(root, ["merge-base", "--is-ancestor", base_revision, "HEAD"])
        if ancestor.returncode != 0:
            return self._reject(task_id, "BASE_REVISION_NOT_ANCESTOR_OF_HEAD")

        allowed = [
            _normalize(p)
            for p in task.get("allowed_paths", [])
            if _normalize(p)
        ]
        violations = []
        for raw in observed["changed_files"]:
            path = _normalize(raw)
            if not allowed or not any(
                path == prefix or path.startswith(prefix + "/")
                for prefix in allowed
            ):
                violations.append(raw)
        if violations:
            self.ledger.append(
                "VALIDATION_REJECTED",
                {
                    "validator_id": validator_id,
                    "reason": "CHANGED_PATH_OUTSIDE_TASK_CONTRACT",
                    "violations": violations,
                },
                task_id=task_id,
            )
            raise ValidationContractError("CHANGED_PATH_OUTSIDE_TASK_CONTRACT")

        outcome = EvidenceOutcome.PASS if returncode == 0 else EvidenceOutcome.FAIL
        detail = {
            "validator_test_artifact": {
                "returncode": returncode,
                "stdout_sha256": stdout_sha256,
                "stderr_sha256": stderr_sha256,
                "duration_ms": duration_ms,
            },
            "workspace_observation": {
                "result_revision": observed["result_revision"],
                "diff_sha256": observed["diff_sha256"],
                "changed_files": observed["changed_files"],
            },
        }
        record = self.evidence.record(
            task_id=task_id,
            actor_id=validator_id,
            actor_role="VALIDATOR",
            suite_id=suite_id,
            suite_digest=suite_digest,
            subject_digest=subject_digest,
            outcome=outcome,
            detail=detail,
        )
        self.ledger.append(
            "VALIDATOR_ARTIFACT_ACCEPTED",
            {
                "evidence_id": record.evidence_id,
                "validator_id": validator_id,
                "suite_id": suite_id,
                "suite_digest": suite_digest,
                "subject_digest": subject_digest,
                "outcome": outcome.value,
                "freshness": record.freshness.value,
                "returncode": returncode,
                "stdout_sha256": stdout_sha256,
                "stderr_sha256": stderr_sha256,
                "duration_ms": duration_ms,
            },
            task_id=task_id,
        )
        return record

    def _task(self, task_id: str) -> dict[str, Any]:
        row = next(
            (
                r for r in self.ledger.events(task_id=task_id)
                if r["event_type"] == "TASK_CREATED"
            ),
            None,
        )
        if row is None:
            raise ValidationContractError("TASK_NOT_ESTABLISHED")
        return row["payload"]

    def _workspace(self, task_id: str) -> dict[str, Any]:
        row = next(
            (
                r for r in reversed(self.ledger.events(task_id=task_id))
                if r["event_type"] == "WORKSPACE_BOUND"
            ),
            None,
        )
        if row is None:
            raise ValidationContractError("WORKSPACE_NOT_ESTABLISHED")
        return row["payload"]

    def _last_builder(self, task_id: str) -> dict[str, Any] | None:
        row = next(
            (
                r for r in reversed(self.ledger.events(task_id=task_id))
                if r["event_type"] == "WORKER_RESULT"
            ),
            None,
        )
        return row["payload"] if row else None

    def _reject(self, task_id: str, reason: str):
        self.ledger.append(
            "VALIDATION_REJECTED",
            {"reason": reason},
            task_id=task_id,
        )
        raise ValidationContractError(reason)
