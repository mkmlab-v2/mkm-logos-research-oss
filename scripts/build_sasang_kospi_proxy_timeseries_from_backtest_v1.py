#!/usr/bin/env python3
"""Build KOSPI-proxy OHLCV CSV from regime-switch backtest metrics [HYPO]."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKTEST = ROOT / "docs/final/artifacts/btc_time_machine_regime_switch_backtest_latest.json"
DEFAULT_OUT = ROOT / "data/myeongni/sasang_kospi_proxy_timeseries_btrack_v1.csv"
META_OUT = ROOT / "reports/sasang_kospi_proxy_timeseries_btrack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(backtest_path: Path, seed: int = 42) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not backtest_path.is_file():
        return [], {"ok": False, "error": "missing_backtest"}
    doc = json.loads(backtest_path.read_text(encoding="utf-8-sig"))
    regime_switch = doc.get("regime_switch") if isinstance(doc.get("regime_switch"), dict) else {}
    per_year = regime_switch.get("per_year") if isinstance(regime_switch.get("per_year"), list) else []
    if not per_year:
        return [], {"ok": False, "error": "missing_regime_switch_per_year"}

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    close = 2500.0
    day = date(2024, 1, 2)
    for yr_row in per_year:
        if not isinstance(yr_row, dict):
            continue
        metrics = yr_row.get("metrics") if isinstance(yr_row.get("metrics"), dict) else {}
        sample_count = int(metrics.get("sample_count") or 0)
        if sample_count <= 0:
            continue
        mu = float(metrics.get("avg_trade_return_pct") or 0.0) / 100.0
        max_dd = float(metrics.get("max_drawdown_pct") or 5.0)
        win_rate = float(metrics.get("win_rate") or 0.5)
        sigma = max(0.003, min(0.06, (max_dd / 100.0) / 7.0 + abs(win_rate - 0.5) * 0.02))
        for _ in range(sample_count):
            ret = mu + rng.gauss(0.0, sigma)
            close = max(100.0, close * (1.0 + ret))
            rows.append({"Date": day.isoformat(), "close": round(close, 4)})
            day += timedelta(days=1)

    meta = {
        "schema": "sasang_kospi_proxy_timeseries_btrack_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "source_backtest_json": str(backtest_path.resolve()).replace("\\", "/"),
        "rows": len(rows),
        "seed": seed,
        "ok": len(rows) >= 40,
        "reproduce": "py scripts/build_sasang_kospi_proxy_timeseries_from_backtest_v1.py",
    }
    return rows, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST)
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=META_OUT)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows, meta = build(args.backtest_json, seed=args.seed)
    if not meta.get("ok"):
        print(json.dumps(meta, ensure_ascii=False))
        return 1

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["Date", "close"])
        writer.writeheader()
        writer.writerows(rows)

    meta["csv_path"] = str(args.out_csv.resolve()).replace("\\", "/")
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "csv": meta["csv_path"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
