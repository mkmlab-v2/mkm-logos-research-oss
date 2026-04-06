#!/usr/bin/env python3
"""Summarize accumulated NotebookLM mega insights JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_10gb.jsonl"
DEFAULT_OUT = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_progress_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize btrack mega insights JSONL.")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tail", type=int, default=2000, help="Analyze last N rows for fast summary.")
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        raise SystemExit(f"missing input: {args.input_jsonl}")

    lines = args.input_jsonl.read_text(encoding="utf-8").splitlines()
    total_rows = len(lines)
    sample = lines[-args.tail :] if args.tail > 0 else lines

    tags = Counter()
    sources = Counter()
    conversations = Counter()
    parsed = 0
    for line in sample:
        try:
            row: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            continue
        parsed += 1
        for t in row.get("tags") or []:
            tags[str(t)] += 1
        for sid in row.get("sources_used") or []:
            sources[str(sid)] += 1
        cid = row.get("conversation_id")
        if cid:
            conversations[str(cid)] += 1

    summary = {
        "schema": "btrack_mega_insight_progress_summary_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] Progress summary for large NotebookLM insight accumulation.",
        "input_jsonl": str(args.input_jsonl),
        "file_size_bytes": args.input_jsonl.stat().st_size,
        "rows_total": total_rows,
        "rows_analyzed": parsed,
        "tail_window": args.tail,
        "top_tags": tags.most_common(20),
        "top_sources": sources.most_common(20),
        "top_conversations": conversations.most_common(10),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

