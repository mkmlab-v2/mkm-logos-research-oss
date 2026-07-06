#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regime-stratified bomyung fuse calibration chain.

  py scripts/run_bomyung_fuse_regime_calibration_v1.py
  py scripts/run_bomyung_fuse_regime_calibration_v1.py --skip-rebuild
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

from scripts.bomyung_fuse_regime_calibration_lib_v1 import (  # noqa: E402
    DEFAULT_KOSPI,
    DEFAULT_PER_DATE,
    evaluate_bomyung_fuse_regime_calibration,
)

OUT = ROOT / "reports/bomyung_fuse_regime_calibration_v1_latest.json"
ART = ROOT / "docs/final/artifacts/bomyung_fuse_regime_calibration_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-date-jsonl", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
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

    doc = evaluate_bomyung_fuse_regime_calibration(
        per_date_path=args.per_date_jsonl,
        kospi_csv=args.kospi_csv,
    )
    doc["generated_at_utc"] = _utc_now()

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(payload, encoding="utf-8")
    ART.write_text(payload, encoding="utf-8")

    cv = doc.get("contract_validation") or {}
    print(
        f"WROTE: {OUT} contract_confirmed={cv.get('contract_confirmed')} "
        f"crisis_trip={cv.get('holdout_crisis_trip_rate')} "
        f"calm_trip={cv.get('holdout_calm_trip_rate')} "
        f"wf_divergence={cv.get('wf_fold_divergence_rates')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
