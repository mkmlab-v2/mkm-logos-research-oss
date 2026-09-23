from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

MODULE = Path(__file__).parents[1] / "experiments" / "mkm_forge_v0a" / "task_worktree.py"
spec = importlib.util.spec_from_file_location("task_worktree", MODULE)
forge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = forge
spec.loader.exec_module(forge)


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    assert cp.returncode == 0, cp.stderr or cp.stdout
    return cp.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init")
    git(r, "config", "user.email", "fixture@example.com")
    git(r, "config", "user.name", "Fixture")
    (r / "src").mkdir()
    (r / "docs").mkdir()
    (r / "src" / "base.py").write_text("VALUE = 1\n", encoding="utf-8")
    (r / "docs" / "readme.md").write_text("base\n", encoding="utf-8")
    git(r, "add", ".")
    git(r, "commit", "-m", "base")
    return r


def create(repo: Path, worktrees: Path, task_id: str):
    return forge.create_task(
        repo,
        worktrees,
        title="fixture task",
        agent_id="codex",
        allowed_paths=["src/**"],
        forbidden_paths=["src/secret/**"],
        task_id=task_id,
    )


def test_distinct_tasks_get_distinct_worktrees_and_branches(repo: Path, tmp_path: Path):
    wt = tmp_path / "worktrees"
    a = create(repo, wt, "TASK-ONE")
    b = create(repo, wt, "TASK-TWO")
    assert a.worktree_path != b.worktree_path
    assert a.branch_name != b.branch_name
    assert Path(a.worktree_path).is_dir()
    assert Path(b.worktree_path).is_dir()


def test_existing_branch_collision_is_rejected(repo: Path, tmp_path: Path):
    git(repo, "branch", "agent/task-collision")
    with pytest.raises(forge.ForgeError, match="branch already exists"):
        create(repo, tmp_path / "worktrees", "TASK-COLLISION")


def test_task_id_path_escape_shape_is_rejected(repo: Path, tmp_path: Path):
    with pytest.raises(forge.ForgeError):
        create(repo, tmp_path / "worktrees", "../escape")


def test_unauthorized_changed_path_is_detected(repo: Path, tmp_path: Path):
    result = create(repo, tmp_path / "worktrees", "TASK-POLICY")
    worktree = Path(result.worktree_path)
    (worktree / "src" / "ok.py").write_text("OK = True\n", encoding="utf-8")
    (worktree / "docs" / "bad.md").write_text("not allowed\n", encoding="utf-8")
    receipt = forge.inspect_task(repo, "TASK-POLICY", persist_receipt=False)
    assert {v["path"] for v in receipt["path_policy_violations"]} == {"docs/bad.md"}
    assert receipt["mechanical_state"] == "MECHANICAL_FAIL"


def test_base_commit_is_recorded_exactly(repo: Path, tmp_path: Path):
    expected = git(repo, "rev-parse", "HEAD")
    result = create(repo, tmp_path / "worktrees", "TASK-BASE")
    assert result.base_revision == expected
    task = forge._load_task(repo, "TASK-BASE")
    assert task["base_revision"] == expected


def test_changed_file_hash_and_coordinate_are_reconstructable(repo: Path, tmp_path: Path):
    result = create(repo, tmp_path / "worktrees", "TASK-HASH")
    worktree = Path(result.worktree_path)
    target = worktree / "src" / "new.py"
    target.write_text("ANSWER = 42\n", encoding="utf-8")
    receipt = forge.inspect_task(repo, "TASK-HASH", persist_receipt=False)
    assert receipt["changed_paths"] == ["src/new.py"]
    coord = receipt["thin_coordinates"][0]
    assert coord["kind"] == "SOURCE"
    assert coord["state"] == "CANDIDATE"
    assert coord["hash"] == forge._sha256(target)


def test_clean_path_policy_never_becomes_semantic_pass(repo: Path, tmp_path: Path):
    result = create(repo, tmp_path / "worktrees", "TASK-CEILING")
    worktree = Path(result.worktree_path)
    (worktree / "src" / "ok.py").write_text("OK = 1\n", encoding="utf-8")
    receipt = forge.inspect_task(repo, "TASK-CEILING", persist_receipt=False)
    assert receipt["path_policy_violations"] == []
    assert receipt["mechanical_state"] == "INCOMPLETE"
    assert receipt["semantic_state"] == "NOT_ADJUDICATED"
    assert receipt["send_gate"] == "HOLD"


def test_close_candidate_does_not_remove_worktree(repo: Path, tmp_path: Path):
    result = create(repo, tmp_path / "worktrees", "TASK-CLOSE")
    worktree = Path(result.worktree_path)
    receipt = forge.close_candidate(repo, "TASK-CLOSE")
    assert worktree.is_dir()
    assert receipt["cleanup_authorization"] == "HUMAN_GATE_REQUIRED"
    assert receipt["destructive_action_executed"] is False
