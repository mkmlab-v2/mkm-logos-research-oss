#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build PR-range manifest: git commits ↔ CENTRAL checkpoints ↔ link JSONL.

PoC for RQ-010 PR-level intent correlation. B-track · research_only.

Usage:
  py scripts/build_coding_intent_pr_manifest_v1.py
  py scripts/build_coding_intent_pr_manifest_v1.py --base gitea/main
  py scripts/build_coding_intent_pr_manifest_v1.py --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENTRAL = WORKSPACE_ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
LINK_LOG = WORKSPACE_ROOT / "reports" / "coding_intent_link_log_v1.jsonl"
LATEST_JSON = WORKSPACE_ROOT / "reports" / "coding_intent_pr_manifest_v1_latest.json"
SCHEMA_PATH = WORKSPACE_ROOT / "docs" / "final" / "schemas" / "coding_intent_pr_manifest_v1.schema.json"
RECORD_SCRIPT = WORKSPACE_ROOT / "scripts" / "record_coding_intent_link_v1.py"

BASE_CANDIDATES = ("gitea/main", "origin/main", "main")


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(args: list[str], *, cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _load_record_module():
    spec = importlib.util.spec_from_file_location("record_coding_intent_link_v1", RECORD_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load {RECORD_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_base_ref(root: Path, base: str | None) -> str:
    if base:
        if _run_git(["rev-parse", "--verify", base], cwd=root):
            return base
        raise SystemExit(f"error: base ref not found: {base}")
    for candidate in BASE_CANDIDATES:
        if _run_git(["rev-parse", "--verify", candidate], cwd=root):
            return candidate
    fallback = _run_git(["rev-parse", "--verify", "HEAD~20"], cwd=root)
    if fallback:
        return "HEAD~20"
    return "HEAD"


def git_commits_in_range(root: Path, base_ref: str) -> list[dict]:
    head = _run_git(["rev-parse", "HEAD"], cwd=root)
    if not head:
        return []
    log = _run_git(
        ["log", f"{base_ref}..HEAD", "--format=%H%x09%s%x09%aI"],
        cwd=root,
    )
    if not log:
        return []
    rows: list[dict] = []
    for line in log.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 2:
            continue
        sha, subject = parts[0], parts[1]
        author_iso = parts[2] if len(parts) > 2 else None
        rows.append({"sha": sha, "subject": subject, "author_iso": author_iso})
    return rows


def load_link_index(log_path: Path) -> dict[str, dict]:
    if not log_path.is_file():
        return {}
    index: dict[str, dict] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        sha = (doc.get("git") or {}).get("head_sha")
        if sha:
            index[sha] = doc
    return index


def _stamp_to_dt(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _author_to_dt(author_iso: str | None) -> datetime | None:
    if not author_iso:
        return None
    try:
        return datetime.fromisoformat(author_iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def pick_checkpoint_for_commit(
    commit_author_iso: str | None,
    checkpoints_newest_first: list[dict],
) -> dict | None:
    """Nearest checkpoint at or before commit time; else closest within 48h."""
    commit_dt = _author_to_dt(commit_author_iso)
    if commit_dt is None or not checkpoints_newest_first:
        return checkpoints_newest_first[0] if checkpoints_newest_first else None

    best_prior: dict | None = None
    best_prior_dt: datetime | None = None
    best_any: tuple[dict, float] | None = None

    for cp in checkpoints_newest_first:
        cp_dt = _stamp_to_dt(cp.get("stamp_utc"))
        if cp_dt is None:
            continue
        delta_h = abs((commit_dt - cp_dt).total_seconds()) / 3600.0
        if best_any is None or delta_h < best_any[1]:
            best_any = (cp, delta_h)
        if cp_dt <= commit_dt and (best_prior_dt is None or cp_dt > best_prior_dt):
            best_prior = cp
            best_prior_dt = cp_dt

    if best_prior is not None:
        return best_prior
    if best_any is not None and best_any[1] <= 48.0:
        return best_any[0]
    return None


def build_manifest(
    *,
    base_ref: str,
    head_sha: str,
    branch: str,
    commits: list[dict],
    checkpoints: list[dict],
    link_index: dict[str, dict],
    note: str | None = None,
) -> dict:
    rows: list[dict] = []
    commits_with_link = 0
    commits_with_checkpoint = 0
    commits_with_intent_ref = 0

    for commit in commits:
        link = link_index.get(commit["sha"])
        cp = pick_checkpoint_for_commit(commit.get("author_iso"), checkpoints)
        intent_ref = None
        if cp:
            intent_ref = cp.get("message")
        if link:
            commits_with_link += 1
            if link.get("link_ok"):
                pass
        if cp:
            commits_with_checkpoint += 1
        if intent_ref:
            commits_with_intent_ref += 1

        rows.append(
            {
                "sha": commit["sha"],
                "subject": commit["subject"],
                "author_iso": commit.get("author_iso"),
                "link_id": link.get("link_id") if link else None,
                "link_ok": link.get("link_ok") if link else None,
                "checkpoint_stamp": cp.get("stamp_utc") if cp else None,
                "checkpoint_message": cp.get("message") if cp else None,
                "intent_ref": intent_ref,
            }
        )

    doc = {
        "schema": "coding_intent_pr_manifest_v1",
        "built_at_utc": _utc_now_z(),
        "research_only": True,
        "base_ref": base_ref,
        "head_sha": head_sha,
        "branch": branch,
        "commit_count": len(rows),
        "rows": rows,
        "coverage": {
            "commits_with_link": commits_with_link,
            "commits_with_checkpoint": commits_with_checkpoint,
            "commits_with_intent_ref": commits_with_intent_ref,
            "checkpoint_total": len(checkpoints),
            "link_log_entries": len(link_index),
        },
        "evidence_paths": [
            "reports/coding_intent_pr_manifest_v1_latest.json",
            "reports/coding_intent_link_log_v1.jsonl",
        ],
    }
    if note:
        doc["note"] = note
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--central-path", type=Path, default=DEFAULT_CENTRAL)
    parser.add_argument("--link-log", type=Path, default=LINK_LOG)
    parser.add_argument("--base", default=None, help="Base ref (default: gitea/main → origin/main → main)")
    parser.add_argument("--out", type=Path, default=LATEST_JSON)
    parser.add_argument("--note", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    central = args.central_path if args.central_path.is_absolute() else root / args.central_path
    link_log = args.link_log if args.link_log.is_absolute() else root / args.link_log
    out_path = args.out if args.out.is_absolute() else root / args.out

    record_mod = _load_record_module()
    base_ref = resolve_base_ref(root, args.base)
    head_sha = _run_git(["rev-parse", "HEAD"], cwd=root) or "0000000"
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root) or "unknown"
    commits = git_commits_in_range(root, base_ref)
    checkpoints = record_mod.list_checkpoints(central, root=root)
    link_index = load_link_index(link_log)

    doc = build_manifest(
        base_ref=base_ref,
        head_sha=head_sha,
        branch=branch,
        commits=commits,
        checkpoints=checkpoints,
        link_index=link_index,
        note=args.note,
    )

    if SCHEMA_PATH.is_file():
        try:
            import jsonschema

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(doc, schema)
        except ImportError:
            pass

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(payload)
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"OK: {out_path}")
    print(
        json.dumps(
            {
                "commit_count": doc["commit_count"],
                "coverage": doc["coverage"],
                "base_ref": base_ref,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
