#!/usr/bin/env python3
"""Map bitcoin-trading KPI snapshot JSONL rows to LOG_METABOLISM_COHORT_ROW_V1 lines.

Derived (not raw HTTP logs):
  - window_start_utc  <- ts_utc
  - egress_pressure     <- watchdog.log_lines (log volume proxy)
  - throttle_events     <- stale_restart + kill_switch_events (governance / fault proxy)
  - trace_scope         <- constant \"btc_trading_kpi\"

Use for pipeline / aggregate tests only; do not claim production server ingress/egress bytes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def row_to_metabolism(line_obj: dict) -> dict | None:
    ts = line_obj.get("ts_utc")
    if not isinstance(ts, str) or not ts.strip():
        return None
    wd = line_obj.get("watchdog")
    if not isinstance(wd, dict):
        return None
    try:
        log_lines = float(wd.get("log_lines") or 0)
    except (TypeError, ValueError):
        return None
    try:
        sr = int(wd.get("stale_restart") or 0)
        ks = int(wd.get("kill_switch_events") or 0)
    except (TypeError, ValueError):
        sr, ks = 0, 0
    throttle = float(sr + ks)
    return {
        "window_start_utc": ts.strip(),
        "trace_scope": "btc_trading_kpi",
        "egress_pressure": log_lines,
        "throttle_events": throttle,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="KPI snapshot JSONL -> log metabolism cohort JSONL.")
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all")
    args = ap.parse_args()
    inp = Path(args.inp).resolve()
    out = Path(args.out).resolve()
    if not inp.is_file():
        print(f"FAIL: not found {inp}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    max_n = int(args.max_rows or 0)
    n_out = 0
    with inp.open(encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = row_to_metabolism(obj)
            if m is None:
                continue
            fout.write(json.dumps(m, ensure_ascii=False) + "\n")
            n_out += 1
            if max_n and n_out >= max_n:
                break
    print(f"WROTE: {out} rows={n_out}")
    return 0 if n_out else 2


if __name__ == "__main__":
    raise SystemExit(main())
