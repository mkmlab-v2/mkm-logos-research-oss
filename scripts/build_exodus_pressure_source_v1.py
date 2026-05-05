#!/usr/bin/env python3
"""Build Exodus five-factor source metrics from public APIs (no paid vendor).

Writes docs/final/artifacts/exodus_pressure_source_latest.json for
build_exodus_pressure_v1.py (source_mode=source_json).

Data mix:
- Binance public klines (BTCUSDT, ETHUSDT) — distribution / vol stress leg.
- CoinGecko public (tether, usd-coin, optional pax-gold) — stable + gold proxy.
- Optional FRED (FRED_API_KEY): GOLDPMGBD228NLBM, DTWEXBGS, NASDAQCOM — macro leg.

0–100 mapping: each factor uses bounded transforms (percent moves, vol ratios,
z-style vs recent window) documented in `raw` for auditability.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "exodus_pressure_source_latest.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _request_json(url: str, timeout: float = 25.0) -> Any:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fred_series(api_key: str, series_id: str, limit: int = 260) -> list[float]:
    q = parse.urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": int(limit),
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=25.0) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows = doc.get("observations")
    out: list[float] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_v = str(row.get("value") or "").strip()
        if not raw_v or raw_v == ".":
            continue
        try:
            out.append(float(raw_v))
        except ValueError:
            continue
    return out


def _binance_daily_klines(symbol: str, limit: int = 90) -> tuple[list[float], list[float]]:
    """Returns closes and quote_volumes, oldest -> newest."""
    q = parse.urlencode({"symbol": symbol, "interval": "1d", "limit": str(limit)})
    url = f"https://api.binance.com/api/v3/klines?{q}"
    rows = _request_json(url)
    if not isinstance(rows, list) or len(rows) < 25:
        raise ValueError(f"binance_klines_insufficient:{symbol}")
    closes: list[float] = []
    qvols: list[float] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 8:
            continue
        closes.append(_to_float(row[4], 0.0))
        qvols.append(_to_float(row[7], 0.0))
    if len(closes) < 25:
        raise ValueError(f"binance_klines_parse:{symbol}")
    return closes, qvols


def _return_n(closes: list[float], n: int) -> float:
    if len(closes) < n + 1:
        return 0.0
    a, b = closes[-(n + 1)], closes[-1]
    if a <= 0.0:
        return 0.0
    return (b / a) - 1.0


def _realized_vol_20d(closes: list[float]) -> float:
    if len(closes) < 22:
        return 0.0
    window = closes[-21:]
    rets: list[float] = []
    for i in range(1, len(window)):
        p, c = window[i - 1], window[i]
        if p <= 0.0:
            continue
        rets.append((c / p) - 1.0)
    if len(rets) < 10:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / len(rets)
    daily_std = var**0.5
    return float(daily_std * (252.0**0.5))


def _coingecko_coin_mcaps_7d(coin_id: str) -> tuple[float | None, float | None]:
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        "?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
    )
    doc = _request_json(url)
    if not isinstance(doc, dict):
        return None, None
    md = doc.get("market_data") if isinstance(doc.get("market_data"), dict) else {}
    ch7 = _to_float(md.get("market_cap_change_percentage_7d"), float("nan"))
    if ch7 != ch7:
        ch7 = _to_float(md.get("price_change_percentage_7d"), float("nan"))
    ch24 = _to_float(md.get("market_cap_change_percentage_24h"), float("nan"))
    if ch24 != ch24:
        ch24 = _to_float(md.get("price_change_percentage_24h"), float("nan"))
    m7 = None if ch7 != ch7 else ch7
    m24 = None if ch24 != ch24 else ch24
    return m7, m24


def _pct_to_score_center50(pct: float, scale: float = 3.0) -> float:
    """Map rough %-change style signal to 0..100 around 50."""
    return _clamp(50.0 + scale * pct, 0.0, 100.0)


def _vol_ratio_latest(qvols: list[float], lookback: int = 30) -> float:
    if len(qvols) < lookback + 2:
        return 1.0
    tail = qvols[-(lookback + 1) : -1]
    med = median(tail) if tail else 1.0
    if med <= 0.0:
        return 1.0
    return float(qvols[-1] / med)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--dry-run", action="store_true", help="Print metrics JSON to stdout only.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    fred_key = (os.environ.get("FRED_API_KEY") or "").strip()

    raw: dict[str, Any] = {"fred_api_key_present": bool(fred_key), "as_of_utc": _utc_now()}

    try:
        btc_c, btc_q = _binance_daily_klines("BTCUSDT", limit=120)
        eth_c, _eth_q = _binance_daily_klines("ETHUSDT", limit=120)
    except (error.URLError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: binance leg failed: {exc}", file=sys.stderr)
        return 1

    r7_btc = _return_n(btc_c, 7)
    r20_btc = _return_n(btc_c, 20)
    r20_eth = _return_n(eth_c, 20)
    vol_spike = _vol_ratio_latest(btc_q, 30)
    rv20_btc = _realized_vol_20d(btc_c)
    hist_rv: list[float] = []
    for end in range(len(btc_c), 22, -1):
        sl = btc_c[:end]
        if len(sl) < 22:
            break
        v = _realized_vol_20d(sl)
        if v > 0.0:
            hist_rv.append(v)
        if len(hist_rv) >= 60:
            break
    rv_med = median(hist_rv) if hist_rv else max(rv20_btc, 1e-9)
    rv_z = (rv20_btc - rv_med) / max(rv_med * 0.25, 1e-9)

    # CEX / distribution pressure: drawdown + volume spike lifts score.
    cex_raw = -110.0 * r7_btc + 18.0 * max(0.0, vol_spike - 1.15)
    cex_net_outflow_index = _clamp(50.0 + 42.0 * (cex_raw / 25.0), 0.0, 100.0)

    raw["binance"] = {
        "btc_r7": round(r7_btc, 8),
        "btc_r20": round(r20_btc, 8),
        "eth_r20": round(r20_eth, 8),
        "vol_spike_ratio": round(vol_spike, 6),
        "btc_rv20_ann": round(rv20_btc, 8),
        "btc_rv_z_style": round(rv_z, 6),
    }

    try:
        usdt7, _ = _coingecko_coin_mcaps_7d("tether")
        usdc7, _ = _coingecko_coin_mcaps_7d("usd-coin")
    except (error.URLError, json.JSONDecodeError) as exc:
        print(f"ERROR: coingecko stable leg failed: {exc}", file=sys.stderr)
        return 1

    stable_parts: list[float] = []
    if usdt7 is not None:
        stable_parts.append(usdt7)
    if usdc7 is not None:
        stable_parts.append(usdc7)
    if not stable_parts:
        print("ERROR: stablecoin 7d mcap change unavailable", file=sys.stderr)
        return 1
    stable_avg = sum(stable_parts) / len(stable_parts)
    # Rising major stable market cap = capital parked / risk-off ammo narrative.
    stablecoin_ammo_index = _pct_to_score_center50(stable_avg, scale=2.8)

    raw["coingecko_stables"] = {"usdt_mcap_chg_7d_pct": usdt7, "usdc_mcap_chg_7d_pct": usdc7, "avg_7d_pct": stable_avg}

    gold_ret_20_fred: float | None = None
    dxy_rv20: float | None = None
    nas_r20: float | None = None
    dxy_fred_desc: list[float] | None = None  # newest-first, reused for dollar history

    def _fred_try(series_id: str, limit: int) -> tuple[list[float], str | None]:
        try:
            rows = _fred_series(fred_key, series_id, limit=limit)
            return rows, None
        except (error.URLError, json.JSONDecodeError, ValueError) as exc:
            return [], f"{series_id}:{exc}"

    if fred_key:
        fred_errors: list[str] = []
        gold, err = _fred_try("GOLDPMGBD228NLBM", 120)
        if err:
            fred_errors.append(err)
        if len(gold) < 25:
            gold2, err2 = _fred_try("GOLDAMGBD228NLBM", 120)
            if err2:
                fred_errors.append(err2)
            if len(gold2) >= 25:
                gold = gold2
        dxy, err = _fred_try("DTWEXBGS", 260)
        if err:
            fred_errors.append(err)
        nas, err = _fred_try("NASDAQCOM", 120)
        if err:
            fred_errors.append(err)
        if dxy:
            dxy_fred_desc = dxy
        if len(gold) >= 25:
            g_old = list(reversed(gold))  # oldest -> newest
            gold_ret_20_fred = _return_n(g_old, 20)
        if len(dxy) >= 40:
            dxy_desc = dxy
            levels = list(reversed(dxy_desc[:40]))
            rets: list[float] = []
            for i in range(1, len(levels)):
                p, c = levels[i - 1], levels[i]
                if p <= 0.0:
                    continue
                rets.append((c / p) - 1.0)
            if len(rets) >= 20:
                tail = rets[-20:]
                m = sum(tail) / len(tail)
                var = sum((x - m) ** 2 for x in tail) / len(tail)
                dxy_rv20 = float((var**0.5) * (252.0**0.5))
        if len(nas) >= 25:
            nas_old = list(reversed(nas))
            nas_r20 = _return_n(nas_old, 20)
        if fred_errors:
            raw["fred_errors"] = fred_errors

    # Gold leg: FRED 20d return if available; else PAXG 7d mcap/price proxy.
    gold_safe_haven_flow: float
    if gold_ret_20_fred is not None:
        # gold_ret_20_fred is fractional (e.g. 0.02 == +2%); map gently around 50.
        gold_safe_haven_flow = _pct_to_score_center50(gold_ret_20_fred * 100.0, scale=14.0)
        raw["gold_source"] = "fred_GOLDPMGBD228NLBM_r20"
    else:
        try:
            pax7, _ = _coingecko_coin_mcaps_7d("pax-gold")
            if pax7 is None:
                raise ValueError("pax_gold_missing")
            gold_safe_haven_flow = _pct_to_score_center50(pax7, scale=3.2)
            raw["gold_source"] = "coingecko_pax_gold_mcap_7d_pct"
        except (error.URLError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: gold proxy failed: {exc}", file=sys.stderr)
            return 1

    # Dollar stress: FRED DXY realized vol elevation; else BTC vol z mapped to 50±.
    if dxy_rv20 is not None and dxy_rv20 > 0.0:
        hist_dxy_rv: list[float] = []
        dxy_full = dxy_fred_desc or []
        if len(dxy_full) >= 80:
            arr = list(reversed(dxy_full))
            for end in range(40, min(len(arr), 200), 5):
                seg = arr[end - 40 : end]
                rets2: list[float] = []
                for i in range(1, len(seg)):
                    p, c = seg[i - 1], seg[i]
                    if p <= 0.0:
                        continue
                    rets2.append((c / p) - 1.0)
                if len(rets2) < 20:
                    continue
                t2 = rets2[-20:]
                m2 = sum(t2) / len(t2)
                v2 = sum((x - m2) ** 2 for x in t2) / len(t2)
                hist_dxy_rv.append(float((v2**0.5) * (252.0**0.5)))
        med_rv = median([x for x in hist_dxy_rv if x > 0.0] or [dxy_rv20])
        dollar_stress_proxy = _clamp(50.0 + 35.0 * ((dxy_rv20 - med_rv) / max(med_rv, 1e-9)), 0.0, 100.0)
        raw["dollar_source"] = "fred_DTWEXBGS_rv20_ann_vs_hist"
        raw["fred_dxy_rv20_ann"] = dxy_rv20
    else:
        dollar_stress_proxy = _clamp(50.0 + 22.0 * rv_z, 0.0, 100.0)
        raw["dollar_source"] = "binance_btc_rv20_z_fallback"

    # Rotation: NASDAQ 20d vs BTC 20d (FRED + Binance); else ETH vs BTC 20d.
    if nas_r20 is not None:
        rel = nas_r20 - r20_btc
        risk_off_rotation = _clamp(50.0 + 90.0 * rel, 0.0, 100.0)
        raw["rotation_source"] = "fred_NASDAQCOM_r20_minus_btc_binance_r20"
        raw["fred_nasdaq_r20"] = nas_r20
    else:
        rel_crypto = r20_eth - r20_btc
        risk_off_rotation = _clamp(50.0 + 120.0 * rel_crypto, 0.0, 100.0)
        raw["rotation_source"] = "binance_eth_r20_minus_btc_r20_proxy"

    metrics = {
        "cex_net_outflow_index": round(cex_net_outflow_index, 6),
        "stablecoin_ammo_index": round(stablecoin_ammo_index, 6),
        "gold_safe_haven_flow": round(gold_safe_haven_flow, 6),
        "dollar_stress_proxy": round(dollar_stress_proxy, 6),
        "risk_off_rotation": round(risk_off_rotation, 6),
    }

    doc = {
        "schema": "exodus_pressure_source_v1",
        "generated_at_utc": _utc_now(),
        "as_of_utc": raw["as_of_utc"],
        "metrics": metrics,
        "raw": raw,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "note": "Public-ingest only; factor names are decision-support indices, not literal on-chain CEX net flow.",
    }

    if args.dry_run:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
