#!/usr/bin/env python3
"""Dump UnifiedTradingMonitor-compatible TE snapshot to monitoring_latest.json (B-track, offline).

Uses TransferEntropyMarketRegimeDetector (btrack_probe_v1) + BTC daily CSV returns.
No live trading, no order APIs.

Output default:
  projects/bitcoin-trading/memory/v2/ops/monitoring_latest.json
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "core"))

DEFAULT_OUT = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "monitoring_latest.json"
)
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"


def _load_btc_returns(csv_path: Path, *, lookback: int) -> list[float]:
    if not csv_path.is_file():
        return []
    rows: list[tuple[str, float]] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date = (row.get("Date") or row.get("date") or "").strip()
            close_raw = row.get("Close") or row.get("close") or row.get("Adj Close")
            try:
                close = float(close_raw) if close_raw not in (None, "") else None
            except (TypeError, ValueError):
                close = None
            if date and close is not None and close > 0:
                rows.append((date, close))
    if len(rows) < 2:
        return []
    rows.sort(key=lambda t: t[0])
    rets: list[float] = []
    for i in range(1, len(rows)):
        p0, p1 = rows[i - 1][1], rows[i][1]
        if p0 > 0:
            rets.append((p1 - p0) / p0)
    return rets[-max(lookback + 1, 5) :]


async def _run_detector(returns: list[float], *, lookback: int) -> dict[str, Any]:
    from transfer_entropy_market_regime_detector import TransferEntropyMarketRegimeDetector

    det = TransferEntropyMarketRegimeDetector(lookback=lookback)
    arr = np.asarray(returns, dtype=float)
    ns = np.zeros_like(arr)
    return await det.detect_market_regime(arr, ns, [], datetime.now(timezone.utc))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    returns = _load_btc_returns(args.btc_csv, lookback=int(args.lookback))
    if len(returns) < 5:
        print(f"error: insufficient BTC returns from {args.btc_csv}", file=sys.stderr)
        return 1

    regime = asyncio.run(_run_detector(returns, lookback=int(args.lookback)))
    doc: dict[str, Any] = {
        "schema": "unified_trading_monitor_snapshot_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "btrack_offline_probe",
        "label": "[HYPO] Monitor TE dump — observation only; not live gating.",
        "regime_analysis": regime,
        "transfer_entropy": regime.get("transfer_entropy"),
        "source_btc_csv": str(args.btc_csv.resolve()),
        "lookback_days": int(args.lookback),
        "fact_safe_note": "Written by dump_unified_trading_monitor_te_snapshot_v1.py using btrack_probe_v1 detector.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} te={regime.get('transfer_entropy')} "
        f"impl={regime.get('implementation')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
