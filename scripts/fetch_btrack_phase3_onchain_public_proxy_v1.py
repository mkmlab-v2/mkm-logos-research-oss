#!/usr/bin/env python3
"""Free public-proxy feed for Phase 3 onchain_exchange_netflow slot (research_only).

NOT Glassnode/CryptoQuant exchange netflow. Combines:
  - blockchain.info estimated on-chain USD volume (daily, ~180d)
  - Binance futures taker buy/sell ratio (daily, ~30d)
  - Binance futures open-interest 1d change (~30d)

Writes: data/btrack/phase3_leading_sensors/onchain_exchange_netflow_measured.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/btrack/phase3_leading_sensors/onchain_exchange_netflow_measured.jsonl"
DEFAULT_REPORT = ROOT / "reports/btrack_phase3_onchain_public_proxy_fetch_v1_latest.json"
CHAIN_CHART = (
    "https://api.blockchain.info/charts/estimated-transaction-volume-usd"
    "?timespan=180days&format=json&sampled=false"
)
SYMBOL = "BTCUSDT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_json(url: str, timeout: float = 25.0) -> Any:
    req = request.Request(
        url=url,
        method="GET",
        headers={"User-Agent": "MKM-BTrack-Phase3-Public-Proxy/1.0 (research_only)"},
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ts_to_date(ts: int) -> str:
    """blockchain.info uses unix seconds; Binance futures data uses milliseconds."""
    sec = ts / 1000.0 if ts >= 1_000_000_000_000 else float(ts)
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%d")


def _z_score(series: list[float], value: float) -> float:
    if len(series) < 8:
        return max(-1.0, min(1.0, value * 3.0))
    mu = statistics.mean(series)
    sd = statistics.pstdev(series) or 1e-12
    return max(-1.0, min(1.0, (value - mu) / sd))


def _pctile_rank(series: list[float], value: float) -> float:
    if not series:
        return 0.5
    below = sum(1 for x in series if x <= value)
    return round(below / len(series), 6)


def _fetch_chain_volume_daily() -> dict[str, float]:
    data = _request_json(CHAIN_CHART)
    values = data.get("values") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return {}
    out: dict[str, float] = {}
    for row in values:
        if not isinstance(row, dict):
            continue
        x, y = row.get("x"), row.get("y")
        if x is None or y is None:
            continue
        try:
            d = _ts_to_date(int(x))
            out[d] = float(y)
        except (TypeError, ValueError):
            continue
    return out


def _fetch_taker_daily(symbol: str) -> dict[str, float]:
    url = (
        "https://fapi.binance.com/futures/data/takerlongshortRatio?"
        + parse.urlencode({"symbol": symbol, "period": "1d", "limit": 500})
    )
    data = _request_json(url)
    if not isinstance(data, list):
        return {}
    out: dict[str, float] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        ts = row.get("timestamp")
        ratio = row.get("buySellRatio")
        if ts is None or ratio is None:
            continue
        try:
            out[_ts_to_date(int(ts))] = float(ratio)
        except (TypeError, ValueError):
            continue
    return out


def _fetch_oi_daily(symbol: str) -> dict[str, float]:
    url = (
        "https://fapi.binance.com/futures/data/openInterestHist?"
        + parse.urlencode({"symbol": symbol, "period": "1d", "limit": 500})
    )
    data = _request_json(url)
    if not isinstance(data, list):
        return {}
    out: dict[str, float] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        ts = row.get("timestamp")
        oi = row.get("sumOpenInterest")
        if ts is None or oi is None:
            continue
        try:
            out[_ts_to_date(int(ts))] = float(oi)
        except (TypeError, ValueError):
            continue
    return out


def _pct_changes(by_day: dict[str, float]) -> dict[str, float]:
    dates = sorted(by_day.keys())
    out: dict[str, float] = {}
    prev: float | None = None
    for d in dates:
        v = by_day[d]
        if prev is not None and prev != 0:
            out[d] = (v - prev) / abs(prev)
        prev = v
    return out


def build_proxy_rows(symbol: str = SYMBOL) -> list[dict[str, Any]]:
    chain_vol = _fetch_chain_volume_daily()
    chain_d1 = _pct_changes(chain_vol)
    taker = _fetch_taker_daily(symbol)
    taker_imb = {d: r - 1.0 for d, r in taker.items()}
    oi = _fetch_oi_daily(symbol)
    oi_d1 = _pct_changes(oi)

    all_dates = sorted(set(chain_d1) | set(taker_imb) | set(oi_d1))
    chain_series = [chain_d1[d] for d in sorted(chain_d1)]
    taker_series = [taker_imb[d] for d in sorted(taker_imb)]
    oi_series = [oi_d1[d] for d in sorted(oi_d1)]

    rows: list[dict[str, Any]] = []
    for d in all_dates:
        parts: list[tuple[str, float, float]] = []
        if d in chain_d1:
            z = _z_score(chain_series, chain_d1[d])
            parts.append(("chain_tx_volume_d1", chain_d1[d], z))
        if d in taker_imb:
            z = _z_score(taker_series, taker_imb[d])
            parts.append(("binance_taker_imbalance", taker_imb[d], z))
        if d in oi_d1:
            z = _z_score(oi_series, oi_d1[d])
            parts.append(("binance_oi_d1", oi_d1[d], z))

        if not parts:
            continue

        weights = {
            "binance_taker_imbalance": 0.45,
            "binance_oi_d1": 0.35,
            "chain_tx_volume_d1": 0.20,
        }
        wsum = sum(weights[p[0]] for p in parts)
        signed = sum(weights[p[0]] * p[2] for p in parts) / wsum if wsum else 0.0
        has_exchange = any(p[0].startswith("binance_") for p in parts)
        quality = "measured_public_proxy_v1" if has_exchange else "measured_chain_activity_proxy_v1"

        raw: dict[str, Any] = {}
        for name, raw_v, _ in parts:
            raw[f"raw_{name}"] = round(raw_v, 8)
        if d in chain_vol:
            raw["raw_chain_tx_volume_usd"] = chain_vol[d]
        if d in taker:
            raw["raw_taker_buy_sell_ratio"] = taker[d]
        if d in oi:
            raw["raw_open_interest_btc"] = oi[d]

        rows.append(
            {
                "eval_date": d,
                "sensor_id": "onchain_exchange_netflow",
                "hypothesis_tier": "B",
                "boundary_ack": True,
                "research_only": True,
                "data_quality": quality,
                "features": {
                    "signed_flow_z": round(signed, 6),
                    "level_pctile": _pctile_rank(
                        [p[2] for p in parts],
                        signed,
                    ),
                    **raw,
                },
                "proxy_components": [p[0] for p in parts],
                "source": "fetch_btrack_phase3_onchain_public_proxy_v1",
                "note": (
                    "NOT Glassnode exchange netflow. Free public proxy: "
                    "chain.info tx volume + Binance taker/OI when available."
                ),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default=SYMBOL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    try:
        rows = build_proxy_rows(args.symbol)
    except (error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: public proxy fetch failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            json.dumps(
                {
                    "n_rows": len(rows),
                    "sample": rows[-3:] if rows else [],
                    "date_range": [rows[0]["eval_date"], rows[-1]["eval_date"]] if rows else [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "schema": "btrack_phase3_onchain_public_proxy_fetch_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "not_glassnode_netflow": True,
        "output": str(args.output),
        "n_rows": len(rows),
        "date_min": rows[0]["eval_date"] if rows else None,
        "date_max": rows[-1]["eval_date"] if rows else None,
        "track_a_promotion": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} ({len(rows)} rows)")
    print(f"WROTE: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
