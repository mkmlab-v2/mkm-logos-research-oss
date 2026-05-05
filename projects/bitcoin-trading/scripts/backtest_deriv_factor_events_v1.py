#!/usr/bin/env python3
"""
backtest_deriv_factor_events_v1

Binance 공개 이력 데이터(USD-M)로 파생 이벤트 백테스트를 수행한다.
- funding rate: /fapi/v1/fundingRate
- open interest hist: /futures/data/openInterestHist
- price klines: /fapi/v1/klines

주의: 연구용(Research-only). 실매매 집행 기능 없음.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE = "https://fapi.binance.com"
BASE_FUTURES_DATA = "https://fapi.binance.com"


def _workspace_root() -> Path:
    here = Path(__file__).resolve()
    if (
        here.parent.name == "scripts"
        and here.parent.parent.name == "bitcoin-trading"
        and here.parents[2].name == "projects"
    ):
        return here.parents[3]
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _get_json(url: str, timeout_sec: float = 20.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-deriv-backtest-v1"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _to_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1500) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        q = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": limit,
            }
        )
        data = _get_json(f"{BASE}/fapi/v1/klines?{q}")
        if not data:
            break
        for row in data:
            # [openTime, open, high, low, close, volume, closeTime, ...]
            out.append(
                {
                    "ts_ms": int(row[0]),
                    "close": float(row[4]),
                    "close_time_ms": int(row[6]),
                }
            )
        last_ts = int(data[-1][0])
        next_cursor = last_ts + 1
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(data) < limit:
            break
        time.sleep(0.05)
    return out


def fetch_funding(symbol: str, start_ms: int, end_ms: int, limit: int = 1000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        q = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": limit,
            }
        )
        data = _get_json(f"{BASE}/fapi/v1/fundingRate?{q}")
        if not data:
            break
        for r in data:
            t = _to_int(r.get("fundingTime"))
            fr = _to_float(r.get("fundingRate"))
            if t is not None and fr is not None:
                out.append({"funding_time_ms": t, "funding_rate": fr})
        last_t = _to_int(data[-1].get("fundingTime"))
        if last_t is None:
            break
        nxt = last_t + 1
        if nxt <= cursor:
            break
        cursor = nxt
        if len(data) < limit:
            break
        time.sleep(0.05)
    out.sort(key=lambda x: x["funding_time_ms"])
    return out


def fetch_oi_hist(symbol: str, period: str, limit: int = 500) -> List[Dict[str, Any]]:
    # Binance futures data endpoint is mostly recent window; pagination by endTime
    out: List[Dict[str, Any]] = []
    end_time: Optional[int] = None
    seen = set()
    for _ in range(200):  # safety
        params = {"symbol": symbol, "period": period, "limit": limit}
        if end_time:
            params["endTime"] = end_time
        q = urllib.parse.urlencode(params)
        data = _get_json(f"{BASE_FUTURES_DATA}/futures/data/openInterestHist?{q}")
        if not data:
            break
        batch: List[Dict[str, Any]] = []
        for r in data:
            ts = _to_int(r.get("timestamp"))
            soi = _to_float(r.get("sumOpenInterest"))
            if ts is None or soi is None:
                continue
            if ts in seen:
                continue
            seen.add(ts)
            batch.append({"ts_ms": ts, "sum_open_interest": soi})
        if not batch:
            break
        batch.sort(key=lambda x: x["ts_ms"])
        out.extend(batch)
        oldest = batch[0]["ts_ms"]
        if end_time is not None and oldest >= end_time:
            break
        end_time = oldest - 1
        time.sleep(0.05)
        if len(data) < limit:
            break
    out.sort(key=lambda x: x["ts_ms"])
    return out


def quantile(vals: List[float], q: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    q = max(0.0, min(1.0, q))
    pos = q * (len(s) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return s[lo]
    w = pos - lo
    return s[lo] * (1 - w) + s[hi] * w


@dataclass
class Pt:
    ts_ms: int
    close: float
    funding_rate: Optional[float]
    oi_delta_pct: Optional[float]


def build_points(
    klines: List[Dict[str, Any]],
    funding: List[Dict[str, Any]],
    oi_hist: List[Dict[str, Any]],
) -> List[Pt]:
    # forward-fill latest funding snapshot
    funding_sorted = sorted(funding, key=lambda x: x["funding_time_ms"])
    oi_sorted = sorted(oi_hist, key=lambda x: x["ts_ms"])
    oi_map = {}
    prev = None
    for r in oi_sorted:
        cur = r["sum_open_interest"]
        if prev is not None and prev > 0:
            oi_map[r["ts_ms"]] = (cur - prev) / prev
        prev = cur

    pts: List[Pt] = []
    fi = 0
    current_f = None
    for k in sorted(klines, key=lambda x: x["ts_ms"]):
        ts = k["ts_ms"]
        while fi < len(funding_sorted) and funding_sorted[fi]["funding_time_ms"] <= ts:
            current_f = funding_sorted[fi]["funding_rate"]
            fi += 1
        pts.append(
            Pt(
                ts_ms=ts,
                close=k["close"],
                funding_rate=current_f,
                oi_delta_pct=oi_map.get(ts),
            )
        )
    return pts


def fwd_ret(pts: List[Pt], i: int, bars: int) -> Optional[float]:
    j = i + bars
    if j >= len(pts):
        return None
    p0 = pts[i].close
    p1 = pts[j].close
    if p0 <= 0:
        return None
    return (p1 / p0) - 1.0


def _stats(a: List[float]) -> Dict[str, Any]:
    if not a:
        return {"count": 0, "mean": None, "win_rate": None}
    return {
        "count": len(a),
        "mean": statistics.mean(a),
        "win_rate": sum(1 for x in a if x > 0) / len(a),
    }


def evaluate_events(pts: List[Pt], bars_list: List[int], cost_bps: float) -> Dict[str, Any]:
    funding_vals = [p.funding_rate for p in pts if p.funding_rate is not None]
    oi_vals = [p.oi_delta_pct for p in pts if p.oi_delta_pct is not None]
    q10f, q90f = quantile(funding_vals, 0.10), quantile(funding_vals, 0.90)
    q10o, q90o = quantile(oi_vals, 0.10), quantile(oi_vals, 0.90)
    cost = cost_bps / 10000.0

    events = [
        ("funding_low", lambda p: q10f is not None and p.funding_rate is not None and p.funding_rate <= q10f),
        ("funding_high", lambda p: q90f is not None and p.funding_rate is not None and p.funding_rate >= q90f),
        ("oi_up", lambda p: q90o is not None and p.oi_delta_pct is not None and p.oi_delta_pct >= q90o),
        ("oi_down", lambda p: q10o is not None and p.oi_delta_pct is not None and p.oi_delta_pct <= q10o),
        (
            "combo_short_squeeze_like",
            lambda p: (
                q10f is not None
                and q90o is not None
                and p.funding_rate is not None
                and p.oi_delta_pct is not None
                and p.funding_rate <= q10f
                and p.oi_delta_pct >= q90o
            ),
        ),
    ]
    out: Dict[str, Any] = {
        "thresholds": {"funding_q10": q10f, "funding_q90": q90f, "oi_q10": q10o, "oi_q90": q90o},
        "events": {},
    }
    ranking: List[Dict[str, Any]] = []
    for name, pred in events:
        idxs = [i for i, p in enumerate(pts) if pred(p)]
        hmap = {}
        for b in bars_list:
            raw, net = [], []
            for i in idxs:
                r = fwd_ret(pts, i, b)
                if r is None:
                    continue
                raw.append(r)
                net.append(r - cost)
            hmap[str(b)] = {
                "raw": _stats(raw),
                "net": _stats(net),
                "mean_bps_net": (statistics.mean(net) * 10000.0) if net else None,
            }
            if net:
                ranking.append(
                    {
                        "event": name,
                        "bars": b,
                        "count": len(net),
                        "mean_bps_net": statistics.mean(net) * 10000.0,
                        "win_rate": sum(1 for x in net if x > 0) / len(net),
                    }
                )
        out["events"][name] = {"event_count": len(idxs), "horizons": hmap}
    ranking.sort(key=lambda x: x["mean_bps_net"], reverse=True)
    out["ranking"] = ranking
    return out


def main() -> int:
    ws = _workspace_root()
    ap = argparse.ArgumentParser(description="Backtest deriv factor events on Binance public historical data.")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", default="5m")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--bars", default="1,3,12", help="forward bars list, comma separated")
    ap.add_argument("--cost-bps", type=float, default=6.0)
    ap.add_argument("--out-json", type=Path, default=ws / "reports" / "deriv_factor_backtest_v1.json")
    args = ap.parse_args()

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=max(1, args.days))
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    bars_list = [int(x.strip()) for x in args.bars.split(",") if x.strip()]

    kl = fetch_klines(args.symbol, args.interval, start_ms, end_ms)
    fd = fetch_funding(args.symbol, start_ms, end_ms)
    oi = fetch_oi_hist(args.symbol, period=args.interval)

    pts = build_points(kl, fd, oi)
    report = {
        "schema": "deriv_factor_backtest_v1",
        "symbol": args.symbol,
        "interval": args.interval,
        "days_requested": args.days,
        "counts": {"klines": len(kl), "funding": len(fd), "oi_hist": len(oi), "points": len(pts)},
        "cost_bps": args.cost_bps,
        "bars": bars_list,
        "result": evaluate_events(pts, bars_list, args.cost_bps),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(args.out_json),
                "counts": report["counts"],
                "top": report["result"]["ranking"][:3],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
