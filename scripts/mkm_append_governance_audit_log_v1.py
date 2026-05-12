#!/usr/bin/env python3
"""Append one governance line to reports/agent_decisions_log.jsonl via log_agent_decision.py."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument("--skip", action="store_true", help="No-op (exit 0).")
    ap.add_argument("--mission-id", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--decision", required=True)
    ap.add_argument("--evidence-path", required=True, help="Repo-relative or absolute path string stored in log.")
    ap.add_argument("--actor", required=True)
    ap.add_argument("--note", default=None)
    ap.add_argument("--risk-level", default=None)
    ap.add_argument("--dry-run", action="store_true", help="Forward to log_agent_decision.py --dry-run.")
    args = ap.parse_args()

    if args.skip:
        return 0

    root = _repo_root(args.repo_root)
    log_py = root / "scripts" / "log_agent_decision.py"
    if not log_py.is_file():
        print(f"WARN: missing {log_py}", file=sys.stderr)
        return 0

    cmd: list[str] = [
        sys.executable,
        str(log_py),
        "--mission-id",
        args.mission_id,
        "--stage",
        args.stage,
        "--decision",
        args.decision,
        "--evidence-path",
        args.evidence_path,
        "--actor",
        args.actor,
    ]
    if args.note is not None:
        cmd += ["--note", args.note]
    if args.risk_level is not None:
        cmd += ["--risk-level", args.risk_level]
    if args.dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        print(json.dumps({"audit_log_warn": proc.stderr or proc.stdout or f"exit={proc.returncode}"}), file=sys.stderr)
        return 0
    if proc.stdout.strip():
        print(proc.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
