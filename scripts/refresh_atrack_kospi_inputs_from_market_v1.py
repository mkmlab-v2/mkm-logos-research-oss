#!/usr/bin/env python3
"""Refresh A-track KOSPI macro inputs + signal from Yahoo Finance (partial auto).

Writes:
  projects/bitcoin-trading/memory/v2/atrack_kospi_inputs_latest.json
  projects/bitcoin-trading/memory/v2/atrack_kospi_signal_latest.json
  append projects/bitcoin-trading/memory/v2/atrack_kospi_signal_history.jsonl

Does not enable trading. Proxy scoring when real API env vars are unset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
MEM = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2"
INPUTS_OUT = MEM / "atrack_kospi_inputs_latest.json"
SIGNAL_OUT = MEM / "atrack_kospi_signal_latest.json"
HISTORY_OUT = MEM / "atrack_kospi_signal_history.jsonl"
POLICY_ID = "atrack_kospi_trigger_portfolio_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pct_change(series, days: int) -> Optional[float]:
    if series is None or len(series) < days + 1:
        return None
    a = float(series.iloc[-1])
    b = float(series.iloc[-(days + 1)])
    if b == 0:
        return None
    return (a / b - 1.0) * 100.0


def _fetch_closes(ticker: str, period: str = "3mo") -> Any:
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if hist is None or hist.empty:
        raise RuntimeError(f"no history for {ticker}")
    return hist["Close"]


def _env_float(name: str) -> Optional[float]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _score_indicators(metrics: Dict[str, Optional[float]]) -> Tuple[Dict[str, int], List[str]]:
    errors: List[str] = []
    brent5 = metrics.get("brent_change_5d_pct")
    brent3 = metrics.get("brent_change_3d_pct")
    usdkrw20 = metrics.get("usdkrw_change_20d_pct")
    kospi20 = metrics.get("kospi_change_20d_pct")
    soxx20 = metrics.get("soxx_change_20d_pct")

    brent_trend = 1 if brent5 is not None and brent5 < 0 else 0
    krw_usd = 0
    if usdkrw20 is not None:
        if usdkrw20 <= -0.5:
            krw_usd = 1
        elif usdkrw20 >= 0.5:
            krw_usd = -1

    foreign_flow = 1 if (kospi20 is not None and kospi20 > 0 and (usdkrw20 is None or usdkrw20 <= 0)) else 0
    semi = 1 if soxx20 is not None and soxx20 > 2.0 else 0
    hormuz = 1 if brent3 is not None and brent3 <= -5.0 else 0

    indicators = {
        "brent_trend": brent_trend,
        "krw_usd_and_dxy": max(-1, min(1, krw_usd)),
        "foreign_net_flow_4w": foreign_flow,
        "korea_semiconductor_exports_yoy": semi,
        "hormuz_shipping_risk": hormuz,
    }
    for k, v in indicators.items():
        if v not in (-1, 0, 1):
            errors.append(f"indicator out of range: {k}={v}")
    return indicators, errors


def _signal_from_indicators(indicators: Dict[str, int]) -> Dict[str, Any]:
    pos = sum(1 for v in indicators.values() if v > 0)
    neg = sum(1 for v in indicators.values() if v < 0)
    score_total = float(sum(max(0, v) for v in indicators.values()))
    if score_total >= 3:
        state = "risk_on"
    elif neg >= 2:
        state = "risk_off"
    else:
        state = "neutral"
    kill = score_total <= 0 and neg >= 3
    return {
        "score_total": score_total,
        "state": state,
        "kill_switch_on": kill,
        "kill_switch_reasons": {
            "two_week_deep_risk": False,
            "triple_shock": kill,
        },
        "indicator_scores": {k: max(0, v) for k, v in indicators.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    if ns.dry_run:
        print("ok", str(INPUTS_OUT), str(SIGNAL_OUT))
        return 0

    try:
        import yfinance  # noqa: F401
    except ImportError:
        print("requires yfinance: pip install yfinance", file=sys.stderr)
        return 2

    prev_inputs: Dict[str, Any] = {}
    if INPUTS_OUT.is_file():
        prev_inputs = json.loads(INPUTS_OUT.read_text(encoding="utf-8-sig"))

    tickers = {
        "brent": "BZ=F",
        "usdkrw": "KRW=X",
        "kospi": "^KS11",
        "soxx": "SOXX",
    }
    errors: List[str] = []
    metrics: Dict[str, Optional[float]] = {}
    try:
        brent = _fetch_closes(tickers["brent"])
        usdkrw = _fetch_closes(tickers["usdkrw"])
        kospi = _fetch_closes(tickers["kospi"])
        soxx = _fetch_closes(tickers["soxx"])
        metrics = {
            "brent_change_5d_pct": _pct_change(brent, 5),
            "brent_change_3d_pct": _pct_change(brent, 3),
            "usdkrw_change_5d_pct": _pct_change(usdkrw, 5),
            "usdkrw_change_20d_pct": _pct_change(usdkrw, 20),
            "kospi_change_20d_pct": _pct_change(kospi, 20),
            "soxx_change_20d_pct": _pct_change(soxx, 20),
            "foreign_flow_4w_real": _env_float("ATRACK_FOREIGN_FLOW_4W_VALUE"),
            "semi_exports_yoy_real": _env_float("ATRACK_SEMI_EXPORTS_YOY_VALUE"),
            "hormuz_risk_index_real": _env_float("ATRACK_HORMUZ_RISK_VALUE"),
        }
    except Exception as exc:  # pragma: no cover
        errors.append(str(exc))

    indicators, ind_errors = _score_indicators(metrics)
    errors.extend(ind_errors)

    manual = prev_inputs.get("manual_carry_over") or {
        "foreign_net_flow_4w": True,
        "korea_semiconductor_exports_yoy": True,
        "hormuz_shipping_risk": True,
    }

    inputs_doc = {
        "schema_version": "v1",
        "updated_at_utc": _utc_now(),
        "source": "auto-yahoo-partial",
        "indicators": indicators,
        "auto_metrics": metrics,
        "manual_carry_over": manual,
        "proxy_mode": {
            "foreign_net_flow_4w": "kospi20d+usdkrw20d proxy",
            "korea_semiconductor_exports_yoy": "soxx20d proxy",
            "hormuz_shipping_risk": "brent3d shock proxy",
        },
        "real_source_mode": {
            "foreign_net_flow_4w": "ATRACK_FOREIGN_FLOW_4W_API_URL",
            "korea_semiconductor_exports_yoy": "ATRACK_SEMI_EXPORTS_YOY_API_URL",
            "hormuz_shipping_risk": "ATRACK_HORMUZ_RISK_API_URL",
        },
        "real_value_mode": {
            "foreign_net_flow_4w": "ATRACK_FOREIGN_FLOW_4W_VALUE",
            "korea_semiconductor_exports_yoy": "ATRACK_SEMI_EXPORTS_YOY_VALUE",
            "hormuz_shipping_risk": "ATRACK_HORMUZ_RISK_VALUE",
        },
        "previous_auto_metrics": prev_inputs.get("auto_metrics") or {},
        "errors": errors,
    }

    sig_core = _signal_from_indicators(indicators)
    signal_doc = {
        "schema_version": "v1",
        "updated_at_utc": inputs_doc["updated_at_utc"],
        "source": inputs_doc["source"],
        **sig_core,
        "data_quality": {"input_error_count": len(errors), "input_errors": errors},
        "policy_id": POLICY_ID,
    }

    MEM.mkdir(parents=True, exist_ok=True)
    INPUTS_OUT.write_text(json.dumps(inputs_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SIGNAL_OUT.write_text(json.dumps(signal_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with HISTORY_OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(signal_doc, ensure_ascii=False) + "\n")

    print(f"WROTE: {INPUTS_OUT}")
    print(f"WROTE: {SIGNAL_OUT}")
    return 0 if not errors else 0  # partial errors still refresh; scheduler should not fail


if __name__ == "__main__":
    raise SystemExit(main())
