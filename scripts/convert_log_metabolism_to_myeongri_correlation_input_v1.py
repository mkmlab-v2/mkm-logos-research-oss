# -*- coding: utf-8 -*-
"""Map LOG_METABOLISM cohort JSONL → log_myeongri_correlation_input_row_v1 JSONL (B-track).

Metabolism rows require: window_start_utc, egress_pressure, throttle_events
(see ``ingest_notebooklm_metabolism_jsonl.REQUIRED``).

Mapping (deterministic proxy — [HYPO] volume/pressure; not production KPI):
  total_requests   = max(1, int(round(egress_pressure)))
  error_count      = max(0, min(total_requests, int(round(throttle_events))))
  unique_trace_ids = max(1, total_requests - error_count)

Each output line is one ``log_myeongri_correlation_input_row_v1`` object.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.ingest_notebooklm_metabolism_jsonl import parse_and_validate_metabolism_jsonl  # noqa: E402

OUT_SCHEMA = "log_myeongri_correlation_input_row_v1"


def _row_metabolism_to_correlation(
    row: Dict[str, Any],
    *,
    run_id: str,
    source: str,
    environment: str,
    window_minutes: int,
) -> Dict[str, Any]:
    ep = float(row["egress_pressure"])
    te = float(row["throttle_events"])
    total = max(1, int(round(ep)))
    err = max(0, min(total, int(round(te))))
    uniq = max(1, total - err)
    return {
        "schema": OUT_SCHEMA,
        "run_metadata": {
            "run_id": run_id,
            "source": source,
            "environment": environment,
        },
        "window_start_utc": str(row["window_start_utc"]),
        "window_minutes": int(window_minutes),
        "metrics": {
            "total_requests": total,
            "error_count": err,
            "unique_trace_ids": uniq,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True, help="LOG_METABOLISM JSONL path")
    ap.add_argument("--out", dest="out", type=Path, required=True, help="Output JSONL path")
    ap.add_argument("--run-id", default="convert_metabolism_to_myeongri_v1_smoke")
    ap.add_argument("--source", default="log_metabolism_cohort")
    ap.add_argument("--environment", default="staging")
    ap.add_argument("--window-minutes", type=int, default=5)
    args = ap.parse_args()

    raw = Path(args.inp).read_text(encoding="utf-8")
    rows, errs = parse_and_validate_metabolism_jsonl(raw)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 2
    if not rows:
        print("ERROR: no valid metabolism rows", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for row in rows:
        lines.append(
            json.dumps(
                _row_metabolism_to_correlation(
                    row,
                    run_id=str(args.run_id),
                    source=str(args.source),
                    environment=str(args.environment),
                    window_minutes=int(args.window_minutes),
                ),
                ensure_ascii=False,
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path} rows={len(lines)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
