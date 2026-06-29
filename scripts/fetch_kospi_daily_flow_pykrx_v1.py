#!/usr/bin/env python3
"""[HYPO] Backfill kospi_daily_flow_external.csv via pykrx (억 KRW net buy).

Requires network + pykrx. Newer pykrx may need KRX_ID/KRX_PW in environment.
Does not run in CI by default. research_only — not Track A / live routing.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPEND = ROOT / "scripts" / "append_kospi_daily_flow_row_v1.py"
ENV_PATH = ROOT / ".env"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH, override=True)


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-date", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--to-date", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    _load_dotenv()

    try:
        from pykrx import stock
    except ImportError:
        print("pip install pykrx required", file=sys.stderr)
        return 2

    d0 = date.fromisoformat(str(args.from_date)[:10])
    d1 = date.fromisoformat(str(args.to_date)[:10])
    if d1 < d0:
        print("invalid date range", file=sys.stderr)
        return 2

    if not os.environ.get("KRX_ID") or not os.environ.get("KRX_PW"):
        print(
            "KRX_ID/KRX_PW not set — pykrx investor-flow may return empty. "
            "Use manual append_kospi_daily_flow_row_v1.py or pending JSON.",
            file=sys.stderr,
        )

    appended = 0
    d = d0
    while d <= d1:
        if d.weekday() >= 5:
            d += timedelta(days=1)
            continue
        ymd = _ymd(d)
        iso = d.isoformat()
        try:
            df = stock.get_market_trading_value_by_investor(ymd, ymd, "KOSPI")
        except Exception as exc:  # noqa: BLE001
            print(f"skip {iso}: {exc}", file=sys.stderr)
            d += timedelta(days=1)
            continue
        if df is None or df.empty:
            d += timedelta(days=1)
            continue
        # Rows: investor type × (매도, 매수, 순매수) — use 순매수 only (not 거래대금 sum).
        def _억_net(row_name: str) -> float:
            if row_name not in df.index:
                return 0.0
            try:
                row = df.loc[row_name]
                if hasattr(row, "index") and "순매수" in row.index:
                    val = float(row["순매수"])
                else:
                    val = float(row)
                return val / 1e8
            except (TypeError, ValueError, KeyError):
                return 0.0

        foreign = _억_net("외국인") + _억_net("기타외국인")
        inst = _억_net("기관합계")
        pension_proxy = _억_net("연기금 등")
        if pension_proxy == 0.0:
            pension_proxy = _억_net("연기금등")
        individual = _억_net("개인")
        program = 0.0
        if args.dry_run:
            print(
                f"DRY {iso} foreign={foreign:.1f} inst={inst:.1f} "
                f"pension_proxy={pension_proxy:.1f} individual={individual:.1f}"
            )
            d += timedelta(days=1)
            continue
        cmd = [
            sys.executable,
            str(APPEND),
            "--date",
            iso,
            "--foreign",
            str(round(foreign, 2)),
            "--institution",
            str(round(inst, 2)),
            "--program",
            str(program),
            "--individual",
            str(round(individual, 2)),
            "--pension-proxy",
            str(round(pension_proxy, 2)),
            "--source-note",
            f"pykrx_investor_net_buy_{ymd}",
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT), check=False).returncode
        if rc == 0:
            appended += 1
        d += timedelta(days=1)

    print(f"appended_or_updated={appended}")
    return 0 if appended > 0 or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
