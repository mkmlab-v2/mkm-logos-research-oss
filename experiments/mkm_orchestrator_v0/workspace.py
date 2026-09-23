from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import re
import subprocess

from .models import AuthorityContract, TaskContract, WorkspaceBinding


class WorktreeError(RuntimeError):
    pass


_SAFE_TASK = re.compile(r"^[A-Za-z0-9._-]+$")


def _run(repo: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *argv],
            cwd=str(repo),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=20,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorktreeError("git operation timed out") from exc


def _ensure_repo(repo: Path) -> None:
    cp = _run(repo, ["rev-parse", "--is-inside-work-tree"])
    if cp.returncode != 0 or cp.stdout.strip().lower() != "true":
        raise WorktreeError("repository_path is not a Git worktree")


def resolve_revision(repo: Path, revision: str) -> str:
    cp = _run(repo, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    if cp.returncode != 0:
        raise WorktreeError("base_revision not found")
    return cp.stdout.strip()


class WorktreeManager:
    """Creates isolated task worktrees. V0 intentionally has no remove operation."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def plan(self, task: TaskContract) -> WorkspaceBinding:
        task.validate()
        if not _SAFE_TASK.fullmatch(task.task_id):
            raise WorktreeError("unsafe task_id")
        repo = Path(task.authority.repository_path).expanduser().resolve()
        _ensure_repo(repo)
        base = resolve_revision(repo, task.authority.base_revision)
        suffix = hashlib.sha256(
            f"{task.authority.repository_id}\n{task.task_id}\n{base}".encode("utf-8")
        ).hexdigest()[:10]
        safe_id = task.task_id.lower().replace(".", "-").replace("_", "-")
        branch = f"mkm/{safe_id}-{suffix}"
        path = (self.root / f"{safe_id}-{suffix}").resolve()
        if os.path.commonpath([str(self.root), str(path)]) != str(self.root):
            raise WorktreeError("planned path escaped worktree root")
        return WorkspaceBinding(
            task_id=task.task_id,
            branch_name=branch,
            worktree_path=str(path),
            base_revision=base,
            repository_path=str(repo),
        )

    def create(self, binding: WorkspaceBinding) -> WorkspaceBinding:
        repo = Path(binding.repository_path).resolve()
        path = Path(binding.worktree_path).resolve()
        if path.exists():
            raise WorktreeError("worktree path already exists")
        cp = _run(
            repo,
            [
                "worktree",
                "add",
                "-b",
                binding.branch_name,
                str(path),
                binding.base_revision,
            ],
        )
        if cp.returncode != 0:
            raise WorktreeError("git worktree add failed: " + cp.stderr.strip()[-1000:])
        actual = resolve_revision(path, "HEAD")
        if actual != binding.base_revision:
            raise WorktreeError("created worktree HEAD does not match base revision")
        return binding
