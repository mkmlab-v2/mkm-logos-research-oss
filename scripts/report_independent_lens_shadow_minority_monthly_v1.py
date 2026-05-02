#!/usr/bin/env python3
"""Roll up independent_lens_fusion_shadow_history.jsonl by UTC calendar month: minority_lens_ids."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = ROOT / "docs/final/artifacts/independent_lens_fusion_shadow_history.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json"

SCHEMA = "independent_lens_shadow_minority_monthly_v1"


def _month_tag(ts: object) -> str:
    s = str(ts or "").strip()
    return s[:7] if len(s) >= 7 else ""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _rollup(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
    """Returns (by_month dict for JSON, totals)."""
    by_month: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total_rows": 0,
            "rows_with_minority_lens": 0,
            "minority_lens_counts": Counter(),
            "narrative_digests": set(),
        }
    )
    totals = {"history_rows_total": 0, "rows_with_minority_lens_total": 0}

    for row in rows:
        totals["history_rows_total"] += 1
        mt = _month_tag(row.get("ts_utc"))
        if not mt:
            continue
        b = by_month[mt]
        b["total_rows"] += 1
        mids = row.get("minority_lens_ids")
        if isinstance(mids, list) and len(mids) > 0:
            b["rows_with_minority_lens"] += 1
            totals["rows_with_minority_lens_total"] += 1
            for lid in mids:
                if isinstance(lid, str) and lid.strip():
                    b["minority_lens_counts"][lid.strip()] += 1
        sha = row.get("conflict_narrative_sha256")
        if isinstance(sha, str) and len(sha) >= 32:
            b["narrative_digests"].add(sha)

    out: dict[str, Any] = {}
    for mt in sorted(by_month.keys()):
        b = by_month[mt]
        counts = dict(sorted(b["minority_lens_counts"].items()))
        out[mt] = {
            "total_rows": b["total_rows"],
            "rows_with_minority_lens": b["rows_with_minority_lens"],
            "minority_lens_counts": counts,
            "distinct_narrative_digest_count": len(b["narrative_digests"]),
        }

    return out, totals


def main() -> int:
    ap = argparse.ArgumentParser(description="Monthly minority_lens_ids rollup from shadow history JSONL.")
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    by_month, totals = _rollup(rows)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "ts_utc": now,
        "hypothesis_tier": "B",
        "source_history_path": str(args.history_jsonl.resolve()),
        "history_rows_total": totals["history_rows_total"],
        "rows_with_minority_lens_total": totals["rows_with_minority_lens_total"],
        "months_observed": sorted(by_month.keys()),
        "by_month": by_month,
        "note": "UTC month from ts_utc; minority_lens_ids absent in legacy rows counts as no minority; not an A-track trigger.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
