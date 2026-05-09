#!/usr/bin/env python3
"""Append latest backfill dependence monitor snapshot to JSONL trend log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_MONITOR = ART / "logos_backfill_dependence_monitor_latest.json"
DEFAULT_LOG = REPORTS / "logos_backfill_dependence_trend_log.jsonl"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Append backfill dependence monitor into trend JSONL.")
    ap.add_argument("--monitor-json", type=Path, default=DEFAULT_MONITOR)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    doc = _load_json(args.monitor_json)
    metrics = doc.get("metrics") or {}
    rec = {
        "schema": "logos_backfill_dependence_trend_record_v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": doc.get("status"),
        "pure_real_corr_candidate_ns": metrics.get("pure_real_corr_candidate_ns"),
        "mixed_backfill_corr_candidate_ns": metrics.get("mixed_backfill_corr_candidate_ns"),
        "delta_mixed_minus_pure": metrics.get("delta_mixed_minus_pure"),
        "source_monitor_json": str(args.monitor_json).replace("\\", "/"),
    }

    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "log_jsonl": str(args.log_jsonl),
                "status": rec["status"],
                "delta_mixed_minus_pure": rec["delta_mixed_minus_pure"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

