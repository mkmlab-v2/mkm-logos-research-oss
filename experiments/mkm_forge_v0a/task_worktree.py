"""MKM Forge V0-A: bounded local task/worktree manager.

Scope:
- local git repositories only
- 1 task = 1 worktree + 1 branch + 1 authority scope
- explicit allowed/forbidden path policy
- base revision + changed-path/hash reconstruction
- inspection and close-candidate receipts
- no merge, push, deployment, credential use, network orchestration, or deletion

Evidence boundary:
- git/test/process success is never promoted to semantic PASS here
- SEND remains HOLD
- destructive cleanup remains HUMAN_GATE
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any
import uuid

SCHEMA = "mkm_forge_task_v0a"
RECEIPT_SCHEMA = "mkm_forge_task_receipt_v0a"
TASK_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")
BRANCH_SAFE_RE = re.compile(r"[^A-Za-z0-9._/-]+")
SEND_GATE = "HOLD"
SEMANTIC_STATE = "NOT_ADJUDICATED"
EVIDENCE_CEILING = "BOUNDED_IMPLEMENTATION_ONLY"


class ForgeError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise ForgeError(cp.stderr.strip() or cp.stdout.strip() or f"git {' '.join(args)} failed")
    return cp


def _repo_root(repo: Path) -> Path:
    cp = _run_git(repo.resolve(), "rev-parse", "--show-toplevel")
    return Path(cp.stdout.strip()).resolve()


def _common_git_dir(repo: Path) -> Path:
    cp = _run_git(repo, "rev-parse", "--git-common-dir")
    raw = Path(cp.stdout.strip())
    return (repo / raw).resolve() if not raw.is_absolute() else raw.resolve()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _canonical_rel(value: str, *, field: str) -> str:
    raw = value.strip().replace("\\", "/")
    p = PurePosixPath(raw)
    if not raw or p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise ForgeError(f"{field} must be a canonical relative path/pattern")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ForgeError(f"{field} must be relative")
    return "/".join(p.parts)


def _canonical_pattern(value: str, *, field: str) -> str:
    return _canonical_rel(value, field=field)


def _validate_task_id(task_id: str) -> str:
    task_id = task_id.strip().upper()
    if not TASK_ID_RE.fullmatch(task_id):
        raise ForgeError("task_id must match [A-Z0-9][A-Z0-9_-]{2,63}")
    return task_id


def _new_task_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"TASK-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def _branch_for(task_id: str) -> str:
    base = f"agent/{task_id.lower()}"
    return BRANCH_SAFE_RE.sub("-", base).strip("-/")


def _safe_child(root: Path, name: str) -> Path:
    root = root.resolve()
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ForgeError("path escapes approved root") from exc
    if candidate == root:
        raise ForgeError("child path must not equal approved root")
    return candidate


def _task_dir(repo: Path, task_id: str) -> Path:
    return _common_git_dir(repo) / "mkm-forge" / "tasks" / task_id


def _task_path(repo: Path, task_id: str) -> Path:
    return _task_dir(repo, task_id) / "task.json"


def _receipt_dir(repo: Path, task_id: str) -> Path:
    return _task_dir(repo, task_id) / "receipts"


def _load_task(repo: Path, task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    path = _task_path(repo, task_id)
    if not path.is_file():
        raise ForgeError(f"unknown task_id: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _path_matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def _policy_violations(paths: list[str], allowed: list[str], forbidden: list[str]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in paths:
        allowed_hit = any(_path_matches(path, pat) for pat in allowed)
        forbidden_hit = any(_path_matches(path, pat) for pat in forbidden)
        if not allowed_hit:
            violations.append({"path": path, "reason": "OUTSIDE_ALLOWED_PATHS"})
        elif forbidden_hit:
            violations.append({"path": path, "reason": "MATCHES_FORBIDDEN_PATH"})
    return violations


def _status_paths(worktree: Path) -> list[str]:
    cp = _run_git(worktree, "status", "--porcelain=v1", "--untracked-files=all")
    out: set[str] = set()
    for line in cp.stdout.splitlines():
        if len(line) < 4:
            continue
        body = line[3:]
        if " -> " in body:
            body = body.split(" -> ", 1)[1]
        if body.startswith('"') and body.endswith('"'):
            body = body[1:-1]
        body = body.replace("\\", "/")
        if body:
            out.add(body)
    return sorted(out)


def _committed_paths(worktree: Path, base_revision: str) -> list[str]:
    cp = _run_git(worktree, "diff", "--name-only", f"{base_revision}...HEAD")
    return sorted({row.strip().replace("\\", "/") for row in cp.stdout.splitlines() if row.strip()})


def _all_changed_paths(worktree: Path, base_revision: str) -> list[str]:
    return sorted(set(_status_paths(worktree)) | set(_committed_paths(worktree, base_revision)))


def _thin_coordinates(worktree: Path, task_id: str, paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in paths:
        abs_path = (worktree / rel).resolve()
        try:
            abs_path.relative_to(worktree.resolve())
        except ValueError:
            continue
        digest = _sha256(abs_path) if abs_path.is_file() else None
        topic = rel.rsplit("/", 1)[-1]
        rows.append({
            "kind": "SOURCE",
            "domain": "DEV",
            "topic": topic,
            "state": "CANDIDATE",
            "privacy": "INTERNAL",
            "source_id": f"src:{digest[:16]}" if digest else f"path:{rel}",
            "hash": digest,
            "path": rel,
            "relations": [{"type": "MODIFIED_BY_TASK", "target": task_id}],
        })
    return rows


@dataclass(frozen=True)
class CreateResult:
    task_id: str
    branch_name: str
    worktree_path: str
    base_revision: str
    state: str
    send_gate: str
    semantic_state: str


def create_task(repo: Path, worktrees_root: Path, *, title: str, agent_id: str,
                allowed_paths: list[str], forbidden_paths: list[str] | None = None,
                base_ref: str = "HEAD", task_id: str | None = None) -> CreateResult:
    repo = _repo_root(repo)
    title = title.strip()
    agent_id = agent_id.strip()
    if not title:
        raise ForgeError("title must be non-empty")
    if not agent_id:
        raise ForgeError("agent_id must be non-empty")
    if not allowed_paths:
        raise ForgeError("at least one allowed path is required")

    allowed = [_canonical_pattern(v, field="allowed_path") for v in allowed_paths]
    forbidden = [_canonical_pattern(v, field="forbidden_path") for v in (forbidden_paths or [])]
    task_id = _validate_task_id(task_id) if task_id else _new_task_id()
    branch = _branch_for(task_id)
    worktrees_root = worktrees_root.resolve()
    worktrees_root.mkdir(parents=True, exist_ok=True)
    worktree = _safe_child(worktrees_root, task_id)

    if _task_path(repo, task_id).exists():
        raise ForgeError(f"task already exists: {task_id}")
    if worktree.exists():
        raise ForgeError(f"worktree path already exists: {worktree}")

    base = _run_git(repo, "rev-parse", f"{base_ref}^{{commit}}").stdout.strip()
    branch_exists = _run_git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    if branch_exists.returncode == 0:
        raise ForgeError(f"branch already exists: {branch}")

    _run_git(repo, "worktree", "add", "-b", branch, str(worktree), base)

    payload = {
        "schema": SCHEMA,
        "schema_version": 1,
        "task_id": task_id,
        "title": title,
        "agent_id": agent_id,
        "repo_root": str(repo),
        "repo_id": repo.name,
        "base_revision": base,
        "base_ref": base_ref,
        "worktree_path": str(worktree),
        "worktrees_root": str(worktrees_root),
        "branch_name": branch,
        "allowed_paths": allowed,
        "forbidden_paths": forbidden,
        "allowed_capabilities": ["READ", "WRITE_WITHIN_ALLOWED_PATHS", "LOCAL_GIT"],
        "forbidden_capabilities": [
            "GIT_PUSH", "MERGE", "DEPLOY", "CREDENTIAL_USE",
            "NETWORK_ESCALATION", "DESTRUCTIVE_CLEANUP"
        ],
        "state": "READY",
        "semantic_state": SEMANTIC_STATE,
        "send_gate": SEND_GATE,
        "evidence_ceiling": EVIDENCE_CEILING,
        "created_at": _utc_now(),
        "auto_next": False,
    }
    _write_json_atomic(_task_path(repo, task_id), payload)
    return CreateResult(task_id, branch, str(worktree), base, "READY", SEND_GATE, SEMANTIC_STATE)


def inspect_task(repo: Path, task_id: str, *, persist_receipt: bool = True) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = _load_task(repo, task_id)
    worktree = Path(task["worktree_path"]).resolve()
    if not worktree.is_dir():
        raise ForgeError("task worktree is missing")

    branch = _run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    head = _run_git(worktree, "rev-parse", "HEAD").stdout.strip()
    changed = _all_changed_paths(worktree, task["base_revision"])
    violations = _policy_violations(changed, task["allowed_paths"], task["forbidden_paths"])
    coordinates = _thin_coordinates(worktree, task["task_id"], changed)

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "receipt_type": "INSPECTION",
        "receipt_id": f"rcpt:{uuid.uuid4().hex}",
        "created_at": _utc_now(),
        "task_id": task["task_id"],
        "base_revision": task["base_revision"],
        "head_revision": head,
        "expected_branch": task["branch_name"],
        "observed_branch": branch,
        "branch_matches": branch == task["branch_name"],
        "changed_paths": changed,
        "path_policy_violations": violations,
        "thin_coordinates": coordinates,
        "mechanical_state": "MECHANICAL_FAIL" if violations or branch != task["branch_name"] else "INCOMPLETE",
        "semantic_state": SEMANTIC_STATE,
        "send_gate": SEND_GATE,
        "evidence_ceiling": EVIDENCE_CEILING,
        "cleanup_authorization": "HUMAN_GATE_REQUIRED",
    }
    if persist_receipt:
        out = _receipt_dir(repo, task["task_id"]) / f"inspect-{receipt['receipt_id'].split(':',1)[1]}.json"
        _write_json_atomic(out, receipt)
        receipt["receipt_path"] = str(out)
    return receipt


def task_status(repo: Path, task_id: str) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = _load_task(repo, task_id)
    inspection = inspect_task(repo, task_id, persist_receipt=False)
    return {
        "task_id": task["task_id"],
        "title": task["title"],
        "agent_id": task["agent_id"],
        "state": task["state"],
        "branch_name": task["branch_name"],
        "worktree_path": task["worktree_path"],
        "base_revision": task["base_revision"],
        "head_revision": inspection["head_revision"],
        "changed_path_count": len(inspection["changed_paths"]),
        "path_policy_violation_count": len(inspection["path_policy_violations"]),
        "mechanical_state": inspection["mechanical_state"],
        "semantic_state": SEMANTIC_STATE,
        "send_gate": SEND_GATE,
        "cleanup_authorization": "HUMAN_GATE_REQUIRED",
    }


def close_candidate(repo: Path, task_id: str) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = _load_task(repo, task_id)
    inspection = inspect_task(repo, task_id, persist_receipt=False)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "receipt_type": "CLOSE_CANDIDATE",
        "receipt_id": f"rcpt:{uuid.uuid4().hex}",
        "created_at": _utc_now(),
        "task_id": task["task_id"],
        "worktree_path": task["worktree_path"],
        "branch_name": task["branch_name"],
        "changed_paths": inspection["changed_paths"],
        "path_policy_violations": inspection["path_policy_violations"],
        "mechanical_state": inspection["mechanical_state"],
        "semantic_state": SEMANTIC_STATE,
        "send_gate": SEND_GATE,
        "cleanup_authorization": "HUMAN_GATE_REQUIRED",
        "destructive_action_executed": False,
        "suggested_manual_commands": [
            f"git -C {task['repo_root']} worktree remove {task['worktree_path']}",
            f"git -C {task['repo_root']} branch -d {task['branch_name']}",
        ],
    }
    out = _receipt_dir(repo, task["task_id"]) / f"close-candidate-{receipt['receipt_id'].split(':',1)[1]}.json"
    _write_json_atomic(out, receipt)
    receipt["receipt_path"] = str(out)
    return receipt


def _json_print(obj: Any) -> None:
    if hasattr(obj, "__dataclass_fields__"):
        obj = asdict(obj)
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    sub = ap.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--worktrees-root", type=Path, required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--agent", required=True)
    p_create.add_argument("--allow", action="append", required=True)
    p_create.add_argument("--forbid", action="append", default=[])
    p_create.add_argument("--base-ref", default="HEAD")
    p_create.add_argument("--task-id")

    for name in ("status", "inspect", "close-candidate"):
        p = sub.add_parser(name)
        p.add_argument("task_id")

    args = ap.parse_args(argv)
    try:
        if args.command == "create":
            result = create_task(args.repo, args.worktrees_root, title=args.title,
                                 agent_id=args.agent, allowed_paths=args.allow,
                                 forbidden_paths=args.forbid, base_ref=args.base_ref,
                                 task_id=args.task_id)
        elif args.command == "status":
            result = task_status(args.repo, args.task_id)
        elif args.command == "inspect":
            result = inspect_task(args.repo, args.task_id)
        elif args.command == "close-candidate":
            result = close_candidate(args.repo, args.task_id)
        else:
            raise ForgeError("unknown command")
    except ForgeError as exc:
        _json_print({"ok": False, "error": str(exc), "send_gate": SEND_GATE})
        return 2

    _json_print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
