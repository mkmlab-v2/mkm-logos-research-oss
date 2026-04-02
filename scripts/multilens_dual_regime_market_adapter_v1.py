#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multilens Thin V2 — market-only dual_regime inputs adapter (v1).

Produces JSON shaped like data/multilens_eval/dual_regime_curated_overlap_v1.json from:
  - Binance public klines (daily OHLCV, close used for returns/vol)
  - Alternative.me Fear & Greed (FGI 0–100 → fear_greed_index 0..1)

Mapping version: ADAPTER_MAPPING_VERSION — OHLC-derived psi/4D; bible_risk_score=0 (no biblical layer).
Not live trading; distinct path from curated overlap benches. See MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json.

Usage:
  py scripts/multilens_dual_regime_market_adapter_v1.py --out data/multilens_eval/dual_regime_market_adapter_v1.json
  py scripts/eval_multilens_harness_v2_thin.py --populate-default-samples --dual-regime-json data/multilens_eval/dual_regime_market_adapter_v1.json ...
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

ADAPTER_MAPPING_VERSION = "1.0.0"
ADAPTER_SCHEMA = "multilens_dual_regime_market_adapter_v1"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
FGI_URL = "https://api.alternative.me/fng/"
USER_AGENT = "multilens-dual-regime-market-adapter/1.0 (+local)"


def _http_get_json(url: str, timeout: float = 45.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _utc_date_from_ms(open_time_ms: int) -> str:
    dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def fetch_binance_daily_closes(
    *,
    symbol: str,
    first_date: str,
    last_date: str,
    http_get_json: Any = _http_get_json,
) -> List[Tuple[str, float]]:
    """Return sorted (calendar_date_utc, close) from Binance daily klines covering [first_date, last_date]."""
    d0 = date.fromisoformat(first_date)
    d1 = date.fromisoformat(last_date)
    start_ms = int(
        datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000
    )
    end_ms = int(
        (datetime(d1.year, d1.month, d1.day, tzinfo=timezone.utc) + timedelta(days=1)).timestamp() * 1000
    )
    out: List[Tuple[str, float]] = []
    cursor = start_ms
    while cursor < end_ms:
        q = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": "1d",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        url = f"{BINANCE_KLINES}?{q}"
        batch = http_get_json(url)
        if not batch:
            break
        for row in batch:
            otime = int(row[0])
            close_px = float(row[4])
            out.append((_utc_date_from_ms(otime), close_px))
        last_open = int(batch[-1][0])
        cursor = last_open + 86400000
        if len(batch) < 1000:
            break
    by_d: Dict[str, float] = {}
    for d, c in out:
        by_d[d] = c
    sorted_dates = sorted(by_d.keys())
    return [(d, by_d[d]) for d in sorted_dates]


def fetch_fgi_normalized_by_date(
    *,
    limit: int = 2000,
    http_get_json: Any = _http_get_json,
) -> Dict[str, float]:
    """Alternative.me FGI: map UTC calendar date → value in [0, 1]."""
    url = f"{FGI_URL}?limit={limit}"
    payload = http_get_json(url)
    data = payload.get("data") or []
    m: Dict[str, float] = {}
    for item in data:
        try:
            ts = int(item.get("timestamp", 0))
            val = float(item.get("value", 50))
        except (TypeError, ValueError):
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        m[dt] = max(0.0, min(1.0, val / 100.0))
    return m


def _index_of_date(sorted_pairs: Sequence[Tuple[str, float]], calendar_date: str) -> int:
    for i, (d, _) in enumerate(sorted_pairs):
        if d == calendar_date:
            return i
    return -1


def _vol_30d(closes: Sequence[float], i: int) -> float:
    if i < 30:
        return 0.02
    window = closes[i - 30 : i + 1]
    rets = [(window[j + 1] - window[j]) / window[j] for j in range(30)]
    return float(statistics.pstdev(rets)) if len(rets) > 1 else 0.02


def _ret_n(closes: Sequence[float], i: int, n: int) -> float:
    if i < n:
        return 0.0
    a, b = closes[i - n], closes[i]
    if a == 0:
        return 0.0
    return float((b - a) / a)


def derive_market_entry_fields(
    *,
    vol_30d: float,
    ret_7d: float,
    ret_14d: float,
    fgi_norm: float,
) -> Dict[str, Any]:
    """
    Deterministic OHLC/FGI → dual_regime scalar fields (market adapter v1).
    bible_risk_score is 0: biblical layer not inferred from price.
    """
    vp = min(1.0, max(0.0, vol_30d / 0.06))
    crash = min(1.0, max(0.0, -ret_7d) * 8.0)
    psi = 0.35 + 0.45 * vp + 0.2 * crash
    psi = max(0.0, min(1.0, psi))

    def axis(x: float) -> float:
        return max(0.12, min(0.88, x))

    s = axis(0.25 + 0.2 * math.tanh(ret_14d * 6.0))
    l = axis(0.25 + 0.15 * math.tanh(vol_30d * 25.0))
    k = axis(0.25 + 0.08 * (fgi_norm - 0.5) * 2.0)
    m_ = axis(0.25 - 0.08 * (fgi_norm - 0.5) * 2.0)

    return {
        "psi_score": psi,
        "bible_risk_score": 0.0,
        "vector_4d": {"S": s, "L": l, "K": k, "M": m_},
        "context_metrics": {"fear_greed_index": fgi_norm},
    }


def build_entry_for_date(
    calendar_date: str,
    sorted_pairs: Sequence[Tuple[str, float]],
    fgi_by_date: Mapping[str, float],
) -> Dict[str, Any]:
    closes = [c for _, c in sorted_pairs]
    i = _index_of_date(sorted_pairs, calendar_date)
    if i < 0:
        raise ValueError(f"No Binance daily row for calendar_date={calendar_date}")
    vol = _vol_30d(closes, i)
    r7 = _ret_n(closes, i, 7)
    r14 = _ret_n(closes, i, 14)
    fgi_n = float(fgi_by_date.get(calendar_date, 0.5))
    if calendar_date not in fgi_by_date:
        pass  # caller may log
    fields = derive_market_entry_fields(vol_30d=vol, ret_7d=r7, ret_14d=r14, fgi_norm=fgi_n)
    return {
        "calendar_date": calendar_date,
        **fields,
        "state_id": None,
        "logos_manuscript_text": None,
        "logos_adjustment_strength": 0.12,
        "adapter_meta": {
            "mapping_version": ADAPTER_MAPPING_VERSION,
            "fgi_source": "alternative.me",
            "ohlc_source": "binance_spot_klines_1d",
        },
    }


def build_payload(
    dates: Sequence[str],
    *,
    symbol: str = "BTCUSDT",
    http_get_json: Any = _http_get_json,
    warn: Any = print,
) -> Dict[str, Any]:
    if not dates:
        raise ValueError("dates list is empty")
    sorted_dates = sorted({str(d) for d in dates})
    first = sorted_dates[0]
    last = sorted_dates[-1]
    warm = date.fromisoformat(first) - timedelta(days=80)
    warm_s = warm.isoformat()
    pairs = fetch_binance_daily_closes(
        symbol=symbol, first_date=warm_s, last_date=last, http_get_json=http_get_json
    )
    fgi_map = fetch_fgi_normalized_by_date(http_get_json=http_get_json)
    missing_fgi = [d for d in sorted_dates if d not in fgi_map]
    if missing_fgi and warn:
        warn(
            f"[multilens market adapter] FGI missing for {len(missing_fgi)} date(s); using 0.5",
            file=sys.stderr,
        )
    entries: List[Dict[str, Any]] = []
    for d in sorted_dates:
        entries.append(build_entry_for_date(d, pairs, fgi_map))
    return {
        "schema": "multilens_dual_regime_inputs_v1",
        "adapter": ADAPTER_SCHEMA,
        "adapter_mapping_version": ADAPTER_MAPPING_VERSION,
        "note": (
            "Market-only adapter: OHLC (Binance) + FGI (Alternative.me). "
            "bible_risk_score=0; not blended with curated overlap benches. "
            "Evaluation / B-track only; no A-track fusion."
        ),
        "symbol": symbol,
        "entries": entries,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    p.add_argument(
        "--curated",
        type=Path,
        default=None,
        help="curated_dates JSON (default: data/multilens_eval/curated_dates_v1.json)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path (default: data/multilens_eval/dual_regime_market_adapter_v1.json)",
    )
    p.add_argument("--symbol", type=str, default="BTCUSDT", help="Binance spot symbol")
    return p


def main() -> None:
    args = _parser().parse_args()
    root = args.workspace_root.resolve()
    curated_path = args.curated or (root / "data" / "multilens_eval" / "curated_dates_v1.json")
    out_path = args.out or (root / "data" / "multilens_eval" / "dual_regime_market_adapter_v1.json")
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    dates = curated.get("dates") or []
    if not isinstance(dates, list) or not dates:
        raise SystemExit(f"No dates in {curated_path}")
    try:
        payload = build_payload(dates, symbol=args.symbol)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error: {exc}") from exc
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "written": str(out_path.resolve()), "rows": len(payload["entries"])}, indent=2))


if __name__ == "__main__":
    main()
