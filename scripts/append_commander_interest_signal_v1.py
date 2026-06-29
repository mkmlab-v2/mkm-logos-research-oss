#!/usr/bin/env python3
"""Append one commander interest signal row to the JSONL log."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import DEFAULT_LOG, ensure_signal_log, resolve_path  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic-id", required=True)
    ap.add_argument("--platform", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--views", type=float, default=0)
    ap.add_argument("--likes", type=float, default=0)
    ap.add_argument("--comments", type=float, default=0)
    ap.add_argument("--shares", type=float, default=0)
    ap.add_argument("--engagement-score", type=float, default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--observed-at-utc", default="")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    observed = args.observed_at_utc.strip() or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "schema": "commander_interest_signal_v1",
        "observed_at_utc": observed,
        "topic_id": args.topic_id.strip(),
        "platform": args.platform.strip(),
        "title": args.title.strip(),
        "url": args.url.strip(),
        "views": args.views,
        "likes": args.likes,
        "comments": args.comments,
        "shares": args.shares,
    }
    if args.engagement_score is not None:
        row["engagement_score"] = args.engagement_score
    if args.note.strip():
        row["note"] = args.note.strip()

    log_path = ensure_signal_log(args.log_jsonl)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "log_path": str(resolve_path(log_path))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
