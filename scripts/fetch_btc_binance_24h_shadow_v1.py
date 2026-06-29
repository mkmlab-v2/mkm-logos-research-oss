#!/usr/bin/env python3
"""Binance BTC public API shadow snapshot for R-IBL dual-leg compare [HYPO][research_only].

Non-SSOT sidecar — primary evening score remains yfinance CSV offline.
No API keys. Network optional; failures return ok=false without raising.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "btc_binance_24h_shadow_latest.json"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_24HR = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_json(url: str, timeout: float = 12.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-R-IBL-shadow/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _direction_from_ret(ret: float, *, eps: float = 0.001) -> str:
    if ret > eps:
        return "up"
    if ret < -eps:
        return "down"
    return "flat"


def _parse_daily_klines(raw: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for k in raw:
        if not isinstance(k, list) or len(k) < 7:
            continue
        open_ms = int(k[0])
        open_p = float(k[1])
        close_p = float(k[4])
        close_ms = int(k[6])
        date_utc = datetime.fromtimestamp(close_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        ret = (close_p - open_p) / open_p if open_p > 0 else 0.0
        rows.append(
            {
                "date_utc": date_utc,
                "open": open_p,
                "close": close_p,
                "return_frac": ret,
                "direction": _direction_from_ret(ret),
            }
        )
    return rows


def fetch_binance_btc_shadow(*, calendar_kst: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "schema": "btc_binance_24h_shadow_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "fetched_at_utc": _utc_now(),
        "calendar_kst": calendar_kst or None,
        "ok": False,
    }
    try:
        klines = _fetch_json(f"{BINANCE_KLINES}?symbol=BTCUSDT&interval=1d&limit=5")
        daily = _parse_daily_klines(klines)
        ticker = _fetch_json(BINANCE_24HR)
        pct_24h = float(ticker.get("priceChangePercent") or 0) / 100.0
        dir_24h = _direction_from_ret(pct_24h)
        last_daily = daily[-1] if daily else {}
        out.update(
            {
                "ok": True,
                "ticker_24h": {
                    "price_change_percent": round(pct_24h * 100, 4),
                    "direction": dir_24h,
                    "last_price": float(ticker.get("lastPrice") or 0),
                },
                "daily_klines": daily,
                "latest_daily": last_daily,
            }
        )
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        out["reason"] = str(exc)[:200]
    return out


def dual_leg_agreement(yf_direction: str, binance_direction: str) -> str:
    y = str(yf_direction or "").lower()
    b = str(binance_direction or "").lower()
    if y in ("insufficient_data", "market_closed") or b in ("", "insufficient_data"):
        return "unknown"
    if y == b:
        return "agree"
    if y == "flat" or b == "flat":
        return "partial"
    return "disagree"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar-kst", default="")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = fetch_binance_btc_shadow(calendar_kst=args.calendar_kst)
    if args.stdout_only:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json} ok={doc.get('ok')}")
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
