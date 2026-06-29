#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI: map latest market_psych v2 CSV row or full timeline to JSON."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_psych_sasang_axis_v2 import (  # noqa: E402
    load_manifest,
    map_row_to_sasang,
    validate_psych_csv_fields,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json",
    )
    ap.add_argument("--out", type=Path, default=ROOT / "reports/market_psych_sasang_axis_map_v2_latest.json")
    ap.add_argument("--last-row-only", action="store_true", default=True)
    ap.add_argument("--all-rows", action="store_true")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    rows = []
    with args.csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_psych_csv_fields(reader.fieldnames, manifest)
        rows = list(reader)
    if not rows:
        print("empty csv", file=sys.stderr)
        return 2

    prev_stress = None
    timeline = []
    for row in rows:
        m = map_row_to_sasang(row, manifest=manifest, prev_stress=prev_stress)
        prev_stress = float(m["byungjeung"]["stress_index"])
        timeline.append({"date": str(row.get("timestamp_utc") or "")[:10], "mapping": m})

    if args.all_rows:
        payload = {"schema": "market_psych_sasang_axis_map_v2", "timeline": timeline}
    else:
        payload = {
            "schema": "market_psych_sasang_axis_map_v2",
            "latest": timeline[-1],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/market_psych_sasang_axis_map_v2_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
