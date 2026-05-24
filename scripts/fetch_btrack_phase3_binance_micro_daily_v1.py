#!/usr/bin/env python3
"""Fetch Binance BTC micro history → Phase 3 leading-sensor measured JSONL (research_only).

Writes (under data/btrack/phase3_leading_sensors/):
  - perp_funding_skew_measured.jsonl   (funding rate daily aggregate)
  - order_flow_imbalance_measured.jsonl (global long/short 1d ratio proxy)

onchain_exchange_netflow: not available on this endpoint — use CSV ingest.

Does not mutate prod score or enable Track A.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "data/btrack/phase3_leading_sensors"
DEFAULT_REPORT = ROOT / "reports/btrack_phase3_binance_micro_fetch_v1_latest.json"
SYMBOL = "BTCUSDT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_json(url: str, timeout: float = 20.0) -> Any:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")


def _z_score(series: list[float], value: float) -> float:
    if len(series) < 8:
        return max(-1.0, min(1.0, value * 200.0))
    mu = statistics.mean(series)
    sd = statistics.pstdev(series) or 1e-12
    return max(-1.0, min(1.0, (value - mu) / sd))


def _pctile_rank(series: list[float], value: float) -> float:
    if not series:
        return 0.5
    below = sum(1 for x in series if x <= value)
    return round(below / len(series), 6)


def _fetch_funding_daily(symbol: str, *, limit: int) -> dict[str, float]:
    """Aggregate mean funding rate per UTC calendar day."""
    url = "https://fapi.binance.com/fapi/v1/fundingRate?" + parse.urlencode({"symbol": symbol, "limit": limit})
    data = _request_json(url)
    if not isinstance(data, list):
        return {}
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in data:
        if not isinstance(row, dict):
            continue
        ft = row.get("fundingTime")
        fr = _to_float(row.get("fundingRate"))
        if ft is None or fr is None:
            continue
        d = _ms_to_date(int(ft))
        buckets[d].append(fr)
    return {d: statistics.mean(v) for d, v in buckets.items()}


def _fetch_long_short_daily(symbol: str, *, limit: int) -> dict[str, float]:
    url = (
        "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?"
        + parse.urlencode({"symbol": symbol, "period": "1d", "limit": limit})
    )
    data = _request_json(url)
    if not isinstance(data, list):
        return {}
    out: dict[str, float] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        ts = row.get("timestamp")
        ratio = _to_float(row.get("longShortRatio"))
        if ts is None or ratio is None:
            continue
        d = _ms_to_date(int(ts))
        out[d] = ratio
    return out


def _canon_row(
    *,
    eval_date: str,
    sensor_id: str,
    signed_flow_z: float,
    level_pctile: float,
    data_quality: str,
    raw: dict[str, Any],
) -> dict[str, Any]:
    feats = {"signed_flow_z": round(signed_flow_z, 6), "level_pctile": round(level_pctile, 6), **raw}
    return {
        "eval_date": eval_date,
        "sensor_id": sensor_id,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "data_quality": data_quality,
        "features": feats,
        "source": "fetch_btrack_phase3_binance_micro_daily_v1",
        "note": "Binance public API daily aggregate; not direction promotion.",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in sorted(rows, key=lambda r: str(r["eval_date"])):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default=SYMBOL)
    ap.add_argument("--funding-limit", type=int, default=1000)
    ap.add_argument("--long-short-limit", type=int, default=180)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    try:
        funding_by_day = _fetch_funding_daily(args.symbol, limit=args.funding_limit)
        ls_by_day = _fetch_long_short_daily(args.symbol, limit=args.long_short_limit)
    except (error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Binance fetch failed: {exc}", file=sys.stderr)
        return 1

    fund_vals = list(funding_by_day.values())
    fund_rows: list[dict[str, Any]] = []
    for d in sorted(funding_by_day.keys()):
        fr = funding_by_day[d]
        z = _z_score(fund_vals, fr)
        fund_rows.append(
            _canon_row(
                eval_date=d,
                sensor_id="perp_funding_skew",
                signed_flow_z=-z,
                level_pctile=_pctile_rank(fund_vals, fr),
                data_quality="measured_binance",
                raw={"raw_funding_rate": fr},
            )
        )

    ls_vals = [ls_by_day[d] - 1.0 for d in sorted(ls_by_day.keys())]
    flow_rows: list[dict[str, Any]] = []
    for d in sorted(ls_by_day.keys()):
        ratio = ls_by_day[d]
        imbalance = ratio - 1.0
        z = _z_score(ls_vals, imbalance)
        flow_rows.append(
            _canon_row(
                eval_date=d,
                sensor_id="order_flow_imbalance",
                signed_flow_z=z,
                level_pctile=_pctile_rank(ls_vals, imbalance),
                data_quality="measured_binance",
                raw={"raw_long_short_ratio": ratio},
            )
        )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "funding_days": len(fund_rows),
                    "long_short_days": len(flow_rows),
                    "funding_sample": fund_rows[-3:] if fund_rows else [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    fund_path = args.out_dir / "perp_funding_skew_measured.jsonl"
    flow_path = args.out_dir / "order_flow_imbalance_measured.jsonl"
    _write_jsonl(fund_path, fund_rows)
    _write_jsonl(flow_path, flow_rows)

    report = {
        "schema": "btrack_phase3_binance_micro_fetch_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "symbol": args.symbol,
        "outputs": {
            "perp_funding_skew": str(fund_path),
            "order_flow_imbalance": str(flow_path),
        },
        "n_funding_days": len(fund_rows),
        "n_long_short_days": len(flow_rows),
        "onchain_note": "Use ingest_btrack_phase3_leading_sensor_feed_v1.py for onchain CSV",
        "track_a_promotion": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {fund_path.resolve()} ({len(fund_rows)} rows)")
    print(f"WROTE: {flow_path.resolve()} ({len(flow_rows)} rows)")
    print(f"WROTE: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
