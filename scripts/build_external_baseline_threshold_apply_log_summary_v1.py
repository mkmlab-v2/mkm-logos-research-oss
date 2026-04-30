#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Build summary artifact from threshold apply log jsonl.
# Keywords: apply log, summary, weekly
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        obj = json.loads(s)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build threshold-apply log summary.")
    ap.add_argument("--apply-log-jsonl", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log_summary_latest.json")
    args = ap.parse_args()

    p_log = resolve(args.apply_log_jsonl)
    out_path = resolve(args.output_json)
    rows = parse_jsonl(p_log)
    by_approver = Counter(str(r.get("approved_by", "unknown")) for r in rows)

    out = {
        "schema": "external_bible_crossref_threshold_apply_log_summary_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "log_ref": str(p_log),
        "apply_count_total": len(rows),
        "last_applied_at_utc": rows[-1].get("applied_at_utc") if rows else None,
        "approver_counts": dict(by_approver),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
