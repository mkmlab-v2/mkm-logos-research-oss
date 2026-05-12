#!/usr/bin/env python3
"""Increment daily run counter for an approval ticket (after successful chain)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TICKET = ART / "mkm_approval_ticket_v1_latest.json"
DEFAULT_RUN_COUNTS = ROOT / "reports" / "mkm_approval_ticket_run_counts_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _increment(state_path: Path, ticket_id: str) -> int:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = _read_json(state_path)
    if not isinstance(data.get("counts"), dict):
        data = {"schema": "mkm_approval_ticket_run_counts_v1", "counts": {}}
    counts = data["counts"]
    key = f"{ticket_id}|{day}"
    n = int(counts.get(key, 0)) + 1
    counts[key] = n
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def _append_audit(repo: Path, *, decision: str, evidence_path: Path, note: str, skip: bool) -> None:
    if skip:
        return
    audit_py = repo / "scripts" / "mkm_append_governance_audit_log_v1.py"
    if not audit_py.is_file():
        return
    cmd = [
        sys.executable,
        str(audit_py),
        "--mission-id",
        "mkm_approval_ticket_v1",
        "--stage",
        "post_chain",
        "--decision",
        decision,
        "--evidence-path",
        str(evidence_path).replace("\\", "/"),
        "--actor",
        "bump_mkm_approval_ticket_run_count_v1.py",
        "--note",
        note[:3800],
    ]
    subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticket-json", type=Path, default=DEFAULT_TICKET)
    ap.add_argument("--runs-state-json", type=Path, default=DEFAULT_RUN_COUNTS)
    ap.add_argument("--skip-audit-log", action="store_true")
    args = ap.parse_args()

    ticket = _read_json(args.ticket_json)
    tid = str(ticket.get("ticket_id") or "").strip()
    caps = dict(ticket.get("execution_caps") or {})
    max_runs = int(caps.get("max_runs_per_day") or 0)
    if not tid or max_runs <= 0:
        print(json.dumps({"ok": True, "skipped": True, "reason": "no_ticket_id_or_max_runs_unlimited"}))
        _append_audit(
            ROOT,
            decision="approval_ticket_run_count_bump_skipped_v1",
            evidence_path=args.ticket_json,
            note=json.dumps({"reason": "no_ticket_id_or_max_runs_unlimited", "ticket_id": tid}),
            skip=bool(args.skip_audit_log),
        )
        return 0
    n = _increment(args.runs_state_json, tid)
    print(json.dumps({"ok": True, "ticket_id": tid, "today_count": n}, ensure_ascii=False))
    _append_audit(
        ROOT,
        decision="approval_ticket_run_count_bump_incremented_v1",
        evidence_path=args.ticket_json,
        note=json.dumps(
            {
                "ticket_id": tid,
                "today_count": n,
                "runs_state": str(args.runs_state_json.resolve()).replace("\\", "/"),
            }
        ),
        skip=bool(args.skip_audit_log),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
