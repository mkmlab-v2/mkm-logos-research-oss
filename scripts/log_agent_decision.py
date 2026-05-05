#!/usr/bin/env python3
"""Append one decision entry to reports/agent_decisions_log.jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--risk-level", default=None)
    parser.add_argument("--retry-count", type=int, default=None)
    parser.add_argument("--note", default=None)
    parser.add_argument("--timestamp", default=None, help="ISO-8601 UTC. Defaults to now().")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = _repo_root(args.repo_root)
    log_path = root / "reports" / "agent_decisions_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": args.timestamp or _iso_now(),
        "mission_id": args.mission_id,
        "stage": args.stage,
        "decision": args.decision,
        "evidence_path": args.evidence_path,
        "actor": args.actor,
    }
    if args.risk_level is not None:
        entry["risk_level"] = args.risk_level
    if args.retry_count is not None:
        entry["retry_count"] = args.retry_count
    if args.note is not None:
        entry["note"] = args.note

    line = json.dumps(entry, ensure_ascii=False)
    if args.dry_run:
        print(line)
        return 0

    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(line + "\n")

    print(f"OK: appended decision log -> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
