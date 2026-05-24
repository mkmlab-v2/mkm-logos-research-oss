#!/usr/bin/env python3
"""Snapshot git/worktree hygiene for Cursor load reduction (read-only + optional prune)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/git_workspace_hygiene_snapshot_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return int(p.returncode), out.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--prune-worktrees",
        action="store_true",
        help="Run git worktree prune before snapshot.",
    )
    args = ap.parse_args()

    prune_log = ""
    if args.prune_worktrees:
        rc, prune_log = _run(["git", "worktree", "prune", "-v"], cwd=ROOT)

    _, wt_list = _run(["git", "worktree", "list"], cwd=ROOT)
    _, status = _run(["git", "status", "--short"], cwd=ROOT)
    status_lines = [ln for ln in status.splitlines() if ln.strip()]

    doc = {
        "schema": "git_workspace_hygiene_snapshot_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "branch": _run(["git", "branch", "--show-current"], cwd=ROOT)[1],
        "porcelain_line_count": len(status_lines),
        "worktree_list": wt_list,
        "worktree_prune_exit_code": 0 if not args.prune_worktrees else rc,
        "worktree_prune_log": prune_log or None,
        "recommendations_ko": [],
    }
    if len(status_lines) > 200:
        doc["recommendations_ko"].append(
            f"porcelain {len(status_lines)}줄 — 커밋·스태시·.gitignore로 working tree 정리 시 Cursor Git UI 부하 감소."
        )
    if "prunable" in wt_list.lower():
        doc["recommendations_ko"].append("prunable worktree — `git worktree prune` 실행 권장.")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "porcelain": len(status_lines)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
