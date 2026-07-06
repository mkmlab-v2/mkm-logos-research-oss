#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MDD / tail-risk safeguard holdout eval for kernel v2 arms.

  py scripts/run_ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1.py
  py scripts/run_ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1.py --skip-rebuild
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ijeoma_kernel_v2_mdd_safeguard_holdout_lib_v1 import (  # noqa: E402
    DEFAULT_KOSPI,
    DEFAULT_PER_DATE,
    evaluate_mdd_safeguard_holdout,
)

OUT = ROOT / "reports/ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1_latest.json"
ART = ROOT / "docs/final/artifacts/ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1_latest.json"
ALIAS = ROOT / "reports/market_signal_holdout_P8_safeguard_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-date-jsonl", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--holdout-days", type=int, default=72)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--skip-rebuild", action="store_true")
    args = ap.parse_args()

    if not args.skip_rebuild:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/build_btrack_market_sasang_per_date_jsonl_v1.py",
                "--date-from",
                "2023-01-01",
                "--date-to",
                "2099-12-31",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    if not args.kospi_csv.is_file():
        print(f"missing kospi_csv: {args.kospi_csv}", file=sys.stderr)
        return 2

    doc = evaluate_mdd_safeguard_holdout(
        per_date_path=args.per_date_jsonl,
        kospi_csv=args.kospi_csv,
        holdout_days=args.holdout_days,
        neutral_bps=args.neutral_bps,
    )
    doc["generated_at_utc"] = _utc_now()

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    ART.parent.mkdir(parents=True, exist_ok=True)
    ART.write_text(payload, encoding="utf-8")
    ALIAS.write_text(payload, encoding="utf-8")

    agg = doc.get("aggregation") or {}
    print(
        f"WROTE: {OUT} hypothesis_supported={doc.get('hypothesis_supported')} "
        f"exploratory_supported={doc.get('exploratory_supported')} "
        f"send_gate={doc.get('send_gate')} "
        f"p13_mdd_reduction={agg.get('primary_mdd_reduction_ratio')} "
        f"baseline_mdd={agg.get('baseline_holdout_max_drawdown')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
