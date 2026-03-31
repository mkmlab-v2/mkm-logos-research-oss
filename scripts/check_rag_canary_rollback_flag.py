#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail when RAG canary rollback flag requests rollback.")
    ap.add_argument(
        "--flag",
        default="reports/constitution/btrack_pilot/rag_canary_rollback_flag_latest.json",
        help="Path to canary rollback flag JSON",
    )
    args = ap.parse_args()

    p = Path(args.flag).resolve()
    if not p.exists():
        print(f"[rag-canary-flag] SKIP: flag file not found: {p}")
        return 0

    data = json.loads(p.read_text(encoding="utf-8"))
    should_rollback = bool(data.get("should_rollback", False))
    reason = str(data.get("reason", "unknown"))
    source_report = str(data.get("source_report", ""))

    if should_rollback:
        print(
            "[rag-canary-flag] BLOCK: rollback requested by canary monitor. "
            f"reason={reason} source_report={source_report}"
        )
        return 1

    print(
        "[rag-canary-flag] PASS: canary is healthy. "
        f"reason={reason} source_report={source_report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
