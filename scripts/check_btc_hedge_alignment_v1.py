#!/usr/bin/env python3
"""Check BTCUSDT hedge alignment (LONG/SHORT amounts) on current account."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "projects" / "bitcoin-trading" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.binance_client import BinanceFuturesClient  # noqa: E402


def main() -> int:
    client = BinanceFuturesClient(testnet=False, maker_only=False)
    rows: list[dict[str, Any]] = client.client.futures_position_information(symbol="BTCUSDT")
    long_amt = 0.0
    short_amt = 0.0
    for r in rows:
        ps = str(r.get("positionSide") or "").upper()
        amt = float(r.get("positionAmt") or 0.0)
        if ps == "LONG":
            long_amt = max(long_amt, amt)
        elif ps == "SHORT":
            short_amt = min(short_amt, amt)
    short_abs = abs(short_amt)
    status = "LONG_ONLY" if long_amt > 0 and short_abs == 0 else "HEDGED_OR_FLAT"
    out = {
        "schema": "btc_hedge_alignment_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "long_amt": long_amt,
        "short_amt": short_amt,
        "short_abs": short_abs,
        "status": status,
        "ok_long_only": status == "LONG_ONLY",
    }
    out_path = ROOT / "reports" / "btc_hedge_alignment_latest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok_long_only"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

