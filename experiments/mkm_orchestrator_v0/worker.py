from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from typing import Protocol

from .models import TaskContract, WorkerResult, WorkspaceBinding


class WorkerAdapter(Protocol):
    worker_id: str

    def run(self, task: TaskContract, workspace: WorkspaceBinding) -> WorkerResult:
        ...


def workspace_subject_digest(path: str | Path) -> str:
    """Digest tracked Git state: HEAD plus working-tree diff/index diff."""
    import subprocess

    root = Path(path).resolve()

    def run(args: list[str]) -> str:
        cp = subprocess.run(
            ["git", *args],
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=20,
            shell=False,
        )
        if cp.returncode != 0:
            raise RuntimeError("git digest operation failed")
        return cp.stdout

    payload = {
        "head": run(["rev-parse", "HEAD"]).strip(),
        "status": run(["status", "--porcelain=v1", "--untracked-files=all"]),
        "diff": run(["diff", "--no-ext-diff", "--no-color"]),
        "diff_cached": run(["diff", "--cached", "--no-ext-diff", "--no-color"]),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class NoopWorker:
    """Test/reference worker: makes no mutation and reports the observed subject."""

    def __init__(self, worker_id: str = "noop-worker"):
        self.worker_id = worker_id

    def run(self, task: TaskContract, workspace: WorkspaceBinding) -> WorkerResult:
        return WorkerResult(
            worker_id=self.worker_id,
            task_id=task.task_id,
            status="PASS",
            subject_digest=workspace_subject_digest(workspace.worktree_path),
            changed_files=(),
            summary="Noop reference worker completed without mutation.",
            metadata={"worker_claim_only": True},
        )
