#!/usr/bin/env python3
"""P17 gold router q05 align — promote gold prefix first (B-track, HYPO).

Fixes q05 router hit@1 via live materialize reorder; refreshes gold eval.

Reproducible:
  py scripts/run_logos_gold_router_q05_align_p17_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_EVAL = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
CHAIN_REPORT = ROOT / "reports/logos_gold_router_canonical_chain_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_gold_router_canonical_chain_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_gold_router_canonical_chain_v1.py")

    if not GOLD_EVAL.is_file():
        print(f"FAIL: missing {GOLD_EVAL}", file=sys.stderr)
        return 1

    gold = json.loads(GOLD_EVAL.read_text(encoding="utf-8-sig"))
    rows = {str(r.get("id")): r for r in gold.get("rows") or []}
    for qid in ("q02", "q05"):
        row = rows.get(qid)
        if not row:
            print(f"FAIL: missing gold row {qid}", file=sys.stderr)
            return 1
        hit1 = (row.get("hit_at_k") or {}).get("1") or {}
        if not hit1.get("router"):
            print(f"FAIL: {qid} router hit@1 false", file=sys.stderr)
            return 1

    if not (gold.get("summary") or {}).get("gold_required_all_pass"):
        print("FAIL: gold_required_all_pass false", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_gold_router_q05_align_p17_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest gold router q05 align p17")

    q05_top = rows["q05"].get("router", {}).get("top_verses", [None])[0]
    print(
        f"gold_required_all_pass=true q02_router_hit@1=true q05_router_hit@1=true "
        f"q05_top_verse={q05_top}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
