#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill stage2 compare history with synthetic daily snapshots.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--compare-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_candidate_compare_v1_latest.json",
    )
    ap.add_argument(
        "--history-jsonl",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_compare_history_v1.jsonl",
    )
    ap.add_argument("--days", type=int, default=7, help="How many daily rows to backfill.")
    ap.add_argument(
        "--overwrite-history",
        action="store_true",
        help="If set, rewrite history file with only generated backfill rows.",
    )
    ns = ap.parse_args()

    compare = _read_json(ns.compare_json)
    now = _utc_now()
    rows: list[dict[str, Any]] = []
    days = max(1, int(ns.days))

    for i in range(days):
        # oldest -> newest daily checkpoints
        ts = now - timedelta(days=(days - 1 - i))
        row = {
            "schema": "agct_sasang_stage2_compare_history_row_v1",
            "appended_at_utc": _fmt_utc(ts),
            "source_generated_at_utc": compare.get("generated_at_utc"),
            "decision_label": compare.get("decision", {}).get("label"),
            "decision_reasons": compare.get("decision", {}).get("reasons", []),
            "baseline_status": compare.get("baseline", {}).get("status"),
            "baseline_repro_trials": compare.get("baseline", {}).get("repro_trials"),
            "candidate_status": compare.get("candidate", {}).get("status"),
            "candidate_decision_label": compare.get("candidate", {}).get("decision_label"),
            "candidate_checks_pass_all": compare.get("candidate", {}).get("checks_pass_all"),
            "backfill": {
                "enabled": True,
                "sequence_index": i + 1,
                "sequence_total": days,
            },
        }
        rows.append(row)

    ns.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if ns.overwrite_history else "a"
    with ns.history_jsonl.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"BACKFILLED: {ns.history_jsonl.resolve()} rows={len(rows)} overwrite={bool(ns.overwrite_history)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
