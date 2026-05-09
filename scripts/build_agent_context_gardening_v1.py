#!/usr/bin/env python3
"""Next-session context artifact: Top-3 focus paths + related tracked files (deterministic git signals)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _workspace_root() -> Path:
    env = (os.environ.get("MKM_WORKSPACE_ROOT") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


WORKSPACE = _workspace_root()
OUT_JSON = WORKSPACE / "docs" / "final" / "artifacts" / "agent_context_gardening_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git(root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.stdout or ""


def _porcelain_modified_paths(root: Path, *, limit: int = 60) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in _git(root, ["status", "--porcelain"]).splitlines():
        if not line.strip():
            continue
        if line.startswith("??"):
            continue
        path = line[3:].strip().strip('"').replace("\\", "/")
        if not path or path.endswith("/"):
            continue
        if path not in seen:
            seen.add(path)
            out.append(path)
        if len(out) >= limit:
            break
    return out


def _recent_commit_paths(root: Path, *, days: int = 4, max_commits: int = 20) -> list[str]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    log_out = _git(
        root,
        ["log", f"--since={since}", f"-n", str(max_commits), "--name-only", "--pretty=format:"],
    )
    out: list[str] = []
    seen: set[str] = set()
    for line in log_out.splitlines():
        line = line.strip().replace("\\", "/")
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def _related_tracked(root: Path, repo_rel: str, *, cap: int = 10) -> list[str]:
    p = Path(repo_rel.replace("\\", "/"))
    parent = p.parent.as_posix()
    if parent in ("", "."):
        return []
    raw = _git(root, ["ls-files", parent]).splitlines()
    rel: list[str] = []
    norm = repo_rel.replace("\\", "/")
    for line in raw:
        f = line.strip().replace("\\", "/")
        if not f or f == norm:
            continue
        rel.append(f)
        if len(rel) >= cap:
            break
    return rel


def build() -> int:
    root = WORKSPACE
    if not (root / ".git").exists() and not (root / ".git").is_file():
        print(json.dumps({"error": "not_a_git_checkout", "root": str(root)}))
        return 2

    modified = _porcelain_modified_paths(root)
    recent = _recent_commit_paths(root)
    ordered: list[str] = []
    seen: set[str] = set()
    for bucket in (modified, recent):
        for p in bucket:
            if p not in seen:
                seen.add(p)
                ordered.append(p)

    top3 = ordered[:3]
    mod_head = set(modified[:30])
    focus_items: list[dict[str, Any]] = []
    for i, path in enumerate(top3, start=1):
        focus_items.append(
            {
                "rank": i,
                "path": path,
                "reason": "modified_worktree" if path in mod_head else "recent_commit",
                "related_paths": _related_tracked(root, path),
            }
        )

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()

    mission_hints: list[str] = []
    ml = root / "MISSION_LOG.md"
    if ml.is_file():
        text = ml.read_text(encoding="utf-8-sig", errors="replace")
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith(("- [ ]", "- [x]", "- [X]")):
                mission_hints.append(s[:500])
            if len(mission_hints) >= 10:
                break

    payload = {
        "schema": "agent_context_gardening_v1",
        "generated_at_utc": _utc_now(),
        "tomorrow_date_utc": tomorrow,
        "inputs": {
            "mission_log_md": "MISSION_LOG.md (optional, typically gitignored)",
            "priority_source_order": ["git_porcelain_modified", "git_recent_commits"],
        },
        "focus_items": focus_items,
        "mission_log_hints": mission_hints,
        "read_next_defaults": [
            "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(OUT_JSON).replace(chr(92), "/"), "focus_items": len(focus_items)}))
    return 0


def main() -> int:
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
