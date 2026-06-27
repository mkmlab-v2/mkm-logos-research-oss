#!/usr/bin/env python3
"""Append or upsert one row in kospi_daily_flow_external.csv (억 KRW net buy).

research_only — manual operator entry when daily investor-flow is published.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "research" / "market_data" / "kospi_daily_flow_external.csv"
FIELDS = (
    "date",
    "foreign_net_buy",
    "institution_net_buy",
    "program_net_buy",
    "individual_net_buy",
    "pension_proxy_net_buy",
    "source_note",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD trading date")
    ap.add_argument("--foreign", type=float, default=0.0, help="Foreign net buy (억 KRW)")
    ap.add_argument("--institution", type=float, default=0.0, help="Institution net buy (억 KRW)")
    ap.add_argument("--program", type=float, default=0.0, help="Program net buy (억 KRW)")
    ap.add_argument("--individual", type=float, default=0.0, help="Individual net buy (억 KRW, optional)")
    ap.add_argument(
        "--pension-proxy",
        type=float,
        default=0.0,
        help="연기금등 net buy proxy (억 KRW; not NPS-isolated)",
    )
    ap.add_argument("--source-note", default="", help="Provenance note")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = ap.parse_args()

    date = str(args.date).strip()[:10]
    if len(date) != 10:
        print("invalid --date", file=sys.stderr)
        return 2

    path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    rows: list[dict[str, str]] = []
    if path.is_file():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            for r in rd:
                if str(r.get("date") or "").strip()[:10] == date:
                    continue
                row_out = {k: str(r.get(k) or "") for k in FIELDS}
                if not row_out.get("pension_proxy_net_buy"):
                    row_out["pension_proxy_net_buy"] = "0"
                rows.append(row_out)

    rows.append(
        {
            "date": date,
            "foreign_net_buy": str(float(args.foreign)),
            "institution_net_buy": str(float(args.institution)),
            "program_net_buy": str(float(args.program)),
            "individual_net_buy": str(float(args.individual)),
            "pension_proxy_net_buy": str(float(args.pension_proxy)),
            "source_note": str(args.source_note or "").strip(),
        }
    )
    rows.sort(key=lambda r: r["date"])

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    print(str(path.resolve()), len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
