#!/usr/bin/env python3
"""Build summarized execution report from cleanup move logs."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


LOG_PATH = Path("reports/workspace_postit_cleanup_moves_v1.jsonl")
JSON_OUT = Path("docs/final/artifacts/workspace_postit_cleanup_execution_report_latest.json")
MD_OUT = Path("docs/final/artifacts/workspace_postit_cleanup_execution_report_latest.md")


def load_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    rows: List[Dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def summarize(rows: List[Dict[str, str]]) -> Dict[str, object]:
    by_session: Dict[str, int] = defaultdict(int)
    by_reason: Dict[str, int] = defaultdict(int)
    for r in rows:
        by_session[r.get("session_dir", "unknown")] += 1
        by_reason[r.get("reason", "unknown")] += 1

    top_sessions = sorted(by_session.items(), key=lambda x: (-x[1], x[0]))
    top_reasons = sorted(by_reason.items(), key=lambda x: (-x[1], x[0]))
    return {
        "total_move_rows": len(rows),
        "session_count": len(by_session),
        "reason_counts": [{"reason": k, "count": v} for k, v in top_reasons],
        "sessions": [{"session_dir": k, "move_count": v} for k, v in top_sessions],
    }


def write_outputs(summary: Dict[str, object], rows: List[Dict[str, str]]) -> None:
    payload = {
        "schema": "workspace_postit_cleanup_execution_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "log_path": str(LOG_PATH.as_posix()),
        "summary": summary,
        "sample_moves": rows[:50],
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Workspace Cleanup Execution Report (latest)",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- total_move_rows: {summary['total_move_rows']}",
        f"- session_count: {summary['session_count']}",
        "",
        "## Move Reasons",
    ]
    for row in summary["reason_counts"][:10]:
        md.append(f"- {row['reason']}: {row['count']}")
    md.append("")
    md.append("## Top Sessions")
    for row in summary["sessions"][:20]:
        md.append(f"- `{row['session_dir']}`: {row['move_count']}")
    md.append("")
    md.append("## Sample Moves")
    for row in rows[:20]:
        md.append(f"- `{row.get('from','')}` -> `{row.get('to','')}`")
    MD_OUT.write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    rows = load_rows(LOG_PATH)
    summary = summarize(rows)
    write_outputs(summary, rows)
    print(f"[ok] cleanup execution report json: {JSON_OUT.as_posix()}")
    print(f"[ok] cleanup execution report md: {MD_OUT.as_posix()}")
    print(f"[ok] move rows: {summary['total_move_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
