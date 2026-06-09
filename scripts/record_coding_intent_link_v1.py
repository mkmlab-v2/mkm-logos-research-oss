#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record a 3-point coding-intent link: git HEAD ↔ CENTRAL checkpoint ↔ gate exit.

PoC for RQ-010 / TRACK_C §3.11(7). B-track · research_only — not Track A promotion.

Usage:
  py scripts/record_coding_intent_link_v1.py record --run-gate
  py scripts/record_coding_intent_link_v1.py record --gate-exit-code 0 --mission-id my-task
  py scripts/record_coding_intent_link_v1.py record --include-diff --run-gate
  py scripts/record_coding_intent_link_v1.py verify
  powershell -File scripts/Install-CodingIntentLinkGitHook_v1.ps1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENTRAL = WORKSPACE_ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
LATEST_JSON = WORKSPACE_ROOT / "reports" / "coding_intent_link_v1_latest.json"
LOG_JSONL = WORKSPACE_ROOT / "reports" / "coding_intent_link_log_v1.jsonl"
SCHEMA_PATH = WORKSPACE_ROOT / "docs" / "final" / "schemas" / "coding_intent_link_v1.schema.json"

MARK_START = "<!-- ATHENA_CHECKPOINT_V1_START -->"
MARK_END = "<!-- ATHENA_CHECKPOINT_V1_END -->"
CHECKPOINT_BULLET_RE = re.compile(
    r"^- \*\*(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\*\* — (?P<message>.+)$"
)

DEFAULT_GATE_CMD = [
    sys.executable,
    "-m",
    "pytest",
    "tests/test_athena_checkpoint.py",
    "-q",
]

HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@"
)


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


def _git_snapshot(root: Path, *, head_sha: str | None, branch: str | None, subject: str | None, dirty: bool | None) -> dict:
    if head_sha is not None:
        return {
            "head_sha": head_sha,
            "branch": branch or "unknown",
            "subject": subject or "",
            "dirty": bool(dirty),
        }
    sha = _run_git(["rev-parse", "HEAD"], cwd=root)
    if not sha:
        return {"head_sha": "0000000", "branch": "unknown", "subject": "", "dirty": True}
    short_branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root) or "unknown"
    subj = _run_git(["log", "-1", "--format=%s"], cwd=root) or ""
    status = _run_git(["status", "--porcelain"], cwd=root)
    return {
        "head_sha": sha,
        "branch": short_branch,
        "subject": subj,
        "dirty": bool(status),
    }


def _relative_repo_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def list_checkpoints(central_path: Path, *, root: Path) -> list[dict]:
    """Return checkpoint bullets newest-first (same order as CENTRAL section)."""
    rel = _relative_repo_path(central_path, root)
    if not central_path.is_file():
        return []
    text = central_path.read_text(encoding="utf-8")
    m = re.search(re.escape(MARK_START) + r"([\s\S]*?)" + re.escape(MARK_END), text)
    if not m:
        return []
    rows: list[dict] = []
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- **"):
            continue
        bullet = CHECKPOINT_BULLET_RE.match(stripped)
        if bullet:
            rows.append(
                {
                    "stamp_utc": bullet.group("stamp"),
                    "message": bullet.group("message").strip(),
                    "central_path": rel,
                }
            )
    return rows


def _latest_checkpoint(central_path: Path, *, root: Path) -> dict:
    rel = _relative_repo_path(central_path, root)
    if not central_path.is_file():
        return {
            "present": False,
            "stamp_utc": None,
            "message": None,
            "central_path": rel,
        }
    text = central_path.read_text(encoding="utf-8")
    m = re.search(re.escape(MARK_START) + r"([\s\S]*?)" + re.escape(MARK_END), text)
    if not m:
        return {
            "present": False,
            "stamp_utc": None,
            "message": None,
            "central_path": rel,
        }
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- **"):
            continue
        bullet = CHECKPOINT_BULLET_RE.match(stripped)
        if bullet:
            return {
                "present": True,
                "stamp_utc": bullet.group("stamp"),
                "message": bullet.group("message").strip(),
                "central_path": rel,
            }
    return {
        "present": False,
        "stamp_utc": None,
        "message": None,
        "central_path": rel,
    }


def _parse_numstat(text: str) -> list[dict]:
    files: list[dict] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add_s, del_s, path = parts
        if add_s == "-" or del_s == "-":
            continue
        files.append(
            {
                "path": path.replace("\\", "/"),
                "insertions": int(add_s),
                "deletions": int(del_s),
            }
        )
    return files


def _merge_file_stats(*chunks: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for chunk in chunks:
        for row in chunk:
            path = row["path"]
            if path not in merged:
                merged[path] = {"path": path, "insertions": 0, "deletions": 0}
            merged[path]["insertions"] += row["insertions"]
            merged[path]["deletions"] += row["deletions"]
    return sorted(merged.values(), key=lambda r: r["path"])


def _git_diff_summary(root: Path, *, dirty: bool, intent_ref: str | None) -> dict:
    if dirty:
        unstaged = _run_git(["diff", "--numstat"], cwd=root) or ""
        staged = _run_git(["diff", "--cached", "--numstat"], cwd=root) or ""
        files = _merge_file_stats(_parse_numstat(unstaged), _parse_numstat(staged))
        scope = "working_tree"
        diff_text = "\n".join(
            x
            for x in [
                _run_git(["diff", "-U0", "--no-color"], cwd=root) or "",
                _run_git(["diff", "--cached", "-U0", "--no-color"], cwd=root) or "",
            ]
            if x
        )
    else:
        show = _run_git(["show", "--numstat", "--format=", "HEAD"], cwd=root) or ""
        files = _parse_numstat(show)
        scope = "last_commit"
        diff_text = _run_git(["show", "-U0", "--no-color", "--format=", "HEAD"], cwd=root) or ""

    total_ins = sum(f["insertions"] for f in files)
    total_del = sum(f["deletions"] for f in files)
    if intent_ref:
        for f in files:
            f["intent_ref"] = intent_ref

    return {
        "scope": scope,
        "file_count": len(files),
        "total_insertions": total_ins,
        "total_deletions": total_del,
        "files": files,
        "_diff_text": diff_text,
    }


def _parse_diff_hunks(diff_text: str, *, intent_ref: str | None, max_hunks: int) -> list[dict]:
    hunks: list[dict] = []
    current_path: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:].replace("\\", "/")
            continue
        if line.startswith("+++ ") and not line.startswith("+++ b/"):
            current_path = line[4:].replace("\\", "/")
            continue
        m = HUNK_HEADER_RE.match(line)
        if not m or not current_path:
            continue
        old_lines = int(m.group("old_lines") or 1)
        new_lines = int(m.group("new_lines") or 1)
        hunks.append(
            {
                "path": current_path,
                "old_start": int(m.group("old_start")),
                "old_lines": old_lines,
                "new_start": int(m.group("new_start")),
                "new_lines": new_lines,
                "intent_ref": intent_ref,
            }
        )
        if len(hunks) >= max_hunks:
            break
    return hunks


def _run_gate(command: list[str], *, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(command, cwd=cwd, check=False)
    return proc.returncode, " ".join(command)


def _link_id(git_sha: str, checkpoint_stamp: str | None, gate_exit: int | None) -> str:
    raw = f"{git_sha}|{checkpoint_stamp or ''}|{gate_exit if gate_exit is not None else 'na'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_record(
    *,
    root: Path,
    central_path: Path,
    mission_id: str | None,
    note: str | None,
    run_gate: bool,
    gate_command: list[str] | None,
    gate_exit_code: int | None,
    git_head_sha: str | None,
    git_branch: str | None,
    git_subject: str | None,
    git_dirty: bool | None,
    checkpoint_stamp: str | None,
    checkpoint_message: str | None,
    include_diff: bool = False,
    max_hunks: int = 32,
    diff_files_override: list[dict] | None = None,
    diff_hunks_override: list[dict] | None = None,
) -> dict:
    recorded_at = _utc_now_z()
    git = _git_snapshot(
        root,
        head_sha=git_head_sha,
        branch=git_branch,
        subject=git_subject,
        dirty=git_dirty,
    )
    if checkpoint_stamp is not None or checkpoint_message is not None:
        checkpoint = {
            "present": bool(checkpoint_stamp and checkpoint_message),
            "stamp_utc": checkpoint_stamp,
            "message": checkpoint_message,
            "central_path": _relative_repo_path(central_path, root),
        }
    else:
        checkpoint = _latest_checkpoint(central_path, root=root)

    gate: dict
    if gate_exit_code is not None:
        gate = {
            "ran": True,
            "command": "(supplied --gate-exit-code)",
            "exit_code": gate_exit_code,
            "ok": gate_exit_code == 0,
        }
    elif run_gate:
        cmd = gate_command or DEFAULT_GATE_CMD
        exit_code, cmd_str = _run_gate(cmd, cwd=root)
        gate = {
            "ran": True,
            "command": cmd_str,
            "exit_code": exit_code,
            "ok": exit_code == 0,
        }
    else:
        gate = {"ran": False, "command": None, "exit_code": None, "ok": False}

    link_ok = (
        git["head_sha"] != "0000000"
        and not git["dirty"]
        and checkpoint["present"]
        and gate["ran"]
        and gate["ok"]
    )

    doc = {
        "schema": "coding_intent_link_v1",
        "recorded_at_utc": recorded_at,
        "link_id": _link_id(git["head_sha"], checkpoint.get("stamp_utc"), gate.get("exit_code")),
        "research_only": True,
        "link_ok": link_ok,
        "git": git,
        "checkpoint": checkpoint,
        "gate": gate,
        "evidence_paths": [
            "reports/coding_intent_link_v1_latest.json",
            "reports/coding_intent_link_log_v1.jsonl",
        ],
    }
    if mission_id:
        doc["mission_id"] = mission_id
    if note:
        doc["note"] = note

    if include_diff:
        intent_ref = checkpoint.get("message") if checkpoint.get("present") else None
        if diff_files_override is not None:
            files = diff_files_override
            summary = {
                "scope": "working_tree",
                "file_count": len(files),
                "total_insertions": sum(f["insertions"] for f in files),
                "total_deletions": sum(f["deletions"] for f in files),
                "files": files,
            }
            if intent_ref:
                for f in summary["files"]:
                    f["intent_ref"] = intent_ref
            hunks = diff_hunks_override or []
        else:
            raw = _git_diff_summary(root, dirty=git["dirty"], intent_ref=intent_ref)
            hunks = _parse_diff_hunks(raw.pop("_diff_text", ""), intent_ref=intent_ref, max_hunks=max_hunks)
            summary = raw
        if hunks:
            summary["hunks"] = hunks
        doc["diff_summary"] = summary

    return doc


def _write_outputs(root: Path, doc: dict, *, dry_run: bool, append_decision_log: bool) -> None:
    latest = root / "reports" / "coding_intent_link_v1_latest.json"
    log_path = root / "reports" / "coding_intent_link_log_v1.jsonl"
    rel_latest = "reports/coding_intent_link_v1_latest.json"

    if dry_run:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return

    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")

    if append_decision_log:
        logger = root / "scripts" / "log_agent_decision.py"
        if logger.is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(logger),
                    "--mission-id",
                    doc.get("mission_id") or "coding_intent_link_v1",
                    "--stage",
                    "record",
                    "--decision",
                    "coding_intent_link_v1",
                    "--evidence-path",
                    rel_latest,
                    "--actor",
                    "record_coding_intent_link_v1.py",
                    "--note",
                    f"link_ok={doc['link_ok']} head={doc['git']['head_sha'][:7]}",
                ],
                cwd=root,
                check=False,
            )

    print(f"OK: {latest}")
    print(f"link_ok: {doc['link_ok']} link_id: {doc['link_id']}")


def cmd_record(args: argparse.Namespace) -> int:
    root = Path(args.repo_root or WORKSPACE_ROOT).resolve()
    central = Path(args.central_path or DEFAULT_CENTRAL)
    if not central.is_absolute():
        central = root / central

    gate_cmd: list[str] | None = None
    if args.gate_command:
        gate_cmd = args.gate_command

    doc = build_record(
        root=root,
        central_path=central,
        mission_id=args.mission_id,
        note=args.note,
        run_gate=args.run_gate,
        gate_command=gate_cmd,
        gate_exit_code=args.gate_exit_code,
        git_head_sha=args.git_head_sha,
        git_branch=args.git_branch,
        git_subject=args.git_subject,
        git_dirty=args.git_dirty,
        checkpoint_stamp=args.checkpoint_stamp,
        checkpoint_message=args.checkpoint_message,
        include_diff=args.include_diff,
        max_hunks=args.max_hunks,
    )
    _write_outputs(root, doc, dry_run=args.dry_run, append_decision_log=not args.skip_decision_log)
    return 0 if doc["link_ok"] or args.allow_partial else 1


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.repo_root or WORKSPACE_ROOT).resolve()
    latest = root / "reports" / "coding_intent_link_v1_latest.json"
    if not latest.is_file():
        print(f"error: missing {latest}", file=sys.stderr)
        return 1

    doc = json.loads(latest.read_text(encoding="utf-8"))
    if doc.get("schema") != "coding_intent_link_v1":
        print("error: schema mismatch", file=sys.stderr)
        return 1

    if SCHEMA_PATH.is_file():
        try:
            import jsonschema
        except ImportError:
            jsonschema = None  # type: ignore[assignment]
        if jsonschema is not None:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(doc, schema)

    live_git = _git_snapshot(root, head_sha=None, branch=None, subject=None, dirty=None)
    cp_path = Path(doc["checkpoint"]["central_path"])
    cp_full = cp_path if cp_path.is_absolute() else root / cp_path
    live_cp = _latest_checkpoint(cp_full, root=root)

    drift = []
    if live_git["head_sha"] != doc["git"]["head_sha"]:
        drift.append("git_head")
    if live_cp.get("stamp_utc") != doc["checkpoint"].get("stamp_utc"):
        drift.append("checkpoint_stamp")

    print(json.dumps({"link_ok": doc.get("link_ok"), "drift": drift, "link_id": doc.get("link_id")}, indent=2))
    if drift and args.strict:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="Capture git + checkpoint + gate into JSON/JSONL")
    rec.add_argument("--central-path", type=Path, default=None)
    rec.add_argument("--mission-id", default=None)
    rec.add_argument("--note", default=None)
    rec.add_argument("--run-gate", action="store_true", help=f"Run gate (default: {' '.join(DEFAULT_GATE_CMD)})")
    rec.add_argument("--gate-command", nargs=argparse.REMAINDER, help="Custom gate command after this flag")
    rec.add_argument("--gate-exit-code", type=int, default=None, help="Use a pre-recorded gate exit code")
    rec.add_argument("--git-head-sha", default=None, help="Test override")
    rec.add_argument("--git-branch", default=None)
    rec.add_argument("--git-subject", default=None)
    rec.add_argument("--git-dirty", action="store_true", default=None)
    rec.add_argument("--no-git-dirty", action="store_false", dest="git_dirty")
    rec.add_argument("--checkpoint-stamp", default=None, help="Test override")
    rec.add_argument("--checkpoint-message", default=None, help="Test override")
    rec.add_argument("--dry-run", action="store_true")
    rec.add_argument("--skip-decision-log", action="store_true")
    rec.add_argument("--allow-partial", action="store_true", help="Exit 0 even when link_ok is false")
    rec.add_argument("--include-diff", action="store_true", help="Attach file numstat + line hunks with checkpoint intent_ref")
    rec.add_argument("--max-hunks", type=int, default=32, help="Max diff hunks to capture (default 32)")

    ver = sub.add_parser("verify", help="Validate latest JSON and optional drift vs live git/checkpoint")
    ver.add_argument("--strict", action="store_true", help="Exit 1 if git/checkpoint drift from recorded snapshot")

    args = parser.parse_args(argv)
    if args.command == "record":
        return cmd_record(args)
    if args.command == "verify":
        return cmd_verify(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
