#!/usr/bin/env python3
"""
build_deriv_factor_panel_v1 — Binance USD-M 선물 파생 3요소 스냅샷/패널 (측정 전용)

Fact-Lock:
  - 인증 없는 공개 REST만 사용 (재현·감사 가능). 실매매·게이트 연동 없음.
  - last_funding_rate: premiumIndex의 직전 정산 구간 펀딩률(거래소 정의).
  - open_interest_base: 계약 수량(베이스). oi_delta_*는 직전 스냅샷(동일 실행 또는 state 파일) 대비.

출력: JSONL 행 + 선택 요약 JSON (reports/ 기본).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_BASE = "https://fapi.binance.com"
ROW_SCHEMA = "deriv_factor_panel_row_v1"
STATE_NAME = "deriv_factor_panel_oi_state_v1.json"
ROWS_NAME = "deriv_factor_panel_rows_v1.jsonl"
SUMMARY_NAME = "deriv_factor_panel_summary_v1.json"


def _workspace_root() -> Path:
    """모노레포 루트 …/workspace (projects/bitcoin-trading/scripts 기준 parents[3])."""
    here = Path(__file__).resolve()
    try:
        if (
            here.parent.name == "scripts"
            and here.parent.parent.name == "bitcoin-trading"
            and here.parents[2].name == "projects"
        ):
            root = here.parents[3]
            if (root / "AGENTS.md").is_file():
                return root
    except IndexError:
        pass
    for parent in here.parents:
        if (
            (parent / "AGENTS.md").is_file()
            and (parent / "projects" / "bitcoin-trading").is_dir()
        ):
            return parent
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout_sec: float = 15.0) -> Tuple[Dict[str, Any], float, int]:
    """GET JSON; return (body, lag_ms, http_status)."""
    t0 = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-deriv-panel-v1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
            lag_ms = (time.perf_counter() - t0) * 1000.0
            status = getattr(resp, "status", 200)
            return json.loads(raw.decode("utf-8")), lag_ms, int(status)
    except urllib.error.HTTPError as e:
        lag_ms = (time.perf_counter() - t0) * 1000.0
        try:
            body = e.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body.strip().startswith("{") else {"raw": body[:500]}
        except Exception:
            payload = {"http_error": str(e)}
        raise RuntimeError(f"HTTP {e.code} {payload}") from e


def fetch_premium_index(base: str, symbol: str) -> Tuple[Dict[str, Any], float]:
    q = urllib.parse.urlencode({"symbol": symbol})
    url = f"{base}/fapi/v1/premiumIndex?{q}"
    data, lag, _ = _fetch_json(url)
    return data, lag


def fetch_open_interest(base: str, symbol: str) -> Tuple[Dict[str, Any], float]:
    q = urllib.parse.urlencode({"symbol": symbol})
    url = f"{base}/fapi/v1/openInterest?{q}"
    data, lag, _ = _fetch_json(url)
    return data, lag


def fetch_ticker_price(base: str, symbol: str) -> Tuple[Dict[str, Any], float]:
    q = urllib.parse.urlencode({"symbol": symbol})
    url = f"{base}/fapi/v1/ticker/price?{q}"
    data, lag, _ = _fetch_json(url)
    return data, lag


@dataclass
class PanelRow:
    schema_id: str
    symbol: str
    collected_at_utc: str
    exchange_event_time_ms: Optional[int]
    lag_client_ms: float
    price_last: Optional[float]
    mark_price: Optional[float]
    index_price: Optional[float]
    last_funding_rate: Optional[float]
    next_funding_time_ms: Optional[int]
    open_interest_base: Optional[float]
    open_interest_quote_usdt: Optional[float]
    oi_delta_abs: Optional[float]
    oi_delta_pct: Optional[float]
    oi_prev_base: Optional[float]
    sample_index: int
    endpoints_lag_ms: Dict[str, float]


def build_row(
    symbol: str,
    sample_index: int,
    prev_oi_base: Optional[float],
    base_url: str,
) -> PanelRow:
    lags: Dict[str, float] = {}
    prem, lag_p = fetch_premium_index(base_url, symbol)
    lags["premiumIndex"] = lag_p
    oi_raw, lag_o = fetch_open_interest(base_url, symbol)
    lags["openInterest"] = lag_o
    tick, lag_t = fetch_ticker_price(base_url, symbol)
    lags["tickerPrice"] = lag_t

    et = prem.get("time")
    try:
        exchange_event_time_ms = int(et) if et is not None else None
    except (TypeError, ValueError):
        exchange_event_time_ms = None

    def _f(x: Any) -> Optional[float]:
        if x is None:
            return None
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    mark = _f(prem.get("markPrice"))
    idx_px = _f(prem.get("indexPrice"))
    last_px = _f(tick.get("price"))
    fund = _f(prem.get("lastFundingRate"))
    try:
        nft = prem.get("nextFundingTime")
        next_funding_time_ms = int(nft) if nft is not None else None
    except (TypeError, ValueError):
        next_funding_time_ms = None

    oi_b = _f(oi_raw.get("openInterest"))
    oi_quote = (oi_b * mark) if (oi_b is not None and mark is not None) else None

    oi_d_abs: Optional[float] = None
    oi_d_pct: Optional[float] = None
    if oi_b is not None and prev_oi_base is not None and prev_oi_base > 0:
        oi_d_abs = oi_b - prev_oi_base
        oi_d_pct = oi_d_abs / prev_oi_base

    lag_total = max(lags.values()) if lags else 0.0

    return PanelRow(
        schema_id=ROW_SCHEMA,
        symbol=symbol,
        collected_at_utc=_utc_now_iso(),
        exchange_event_time_ms=exchange_event_time_ms,
        lag_client_ms=round(lag_total, 3),
        price_last=last_px,
        mark_price=mark,
        index_price=idx_px,
        last_funding_rate=fund,
        next_funding_time_ms=next_funding_time_ms,
        open_interest_base=oi_b,
        open_interest_quote_usdt=round(oi_quote, 6) if oi_quote is not None else None,
        oi_delta_abs=round(oi_d_abs, 8) if oi_d_abs is not None else None,
        oi_delta_pct=round(oi_d_pct, 8) if oi_d_pct is not None else None,
        oi_prev_base=round(prev_oi_base, 8) if prev_oi_base is not None else None,
        sample_index=sample_index,
        endpoints_lag_ms={k: round(v, 3) for k, v in lags.items()},
    )


def load_state(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_state(path: Path, symbol: str, oi_base: float, collected_at: str) -> None:
    payload = {
        "schema": "deriv_factor_panel_oi_state_v1",
        "symbol": symbol,
        "last_open_interest_base": oi_base,
        "updated_at_utc": collected_at,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def summarize(rows: List[PanelRow]) -> Dict[str, Any]:
    if not rows:
        return {"schema": "deriv_factor_panel_summary_v1", "count": 0}

    def nums(getter):
        return [getter(r) for r in rows if getter(r) is not None]

    fr = nums(lambda r: r.last_funding_rate)
    oi_pct = nums(lambda r: r.oi_delta_pct)
    px = nums(lambda r: r.price_last or r.mark_price)
    lags = [r.lag_client_ms for r in rows]

    out: Dict[str, Any] = {
        "schema": "deriv_factor_panel_summary_v1",
        "count": len(rows),
        "symbol": rows[0].symbol,
        "funding_rate": _stats(fr),
        "oi_delta_pct_sample": _stats(oi_pct),
        "price": _stats(px),
        "lag_client_ms": _stats(lags),
    }
    if len(px) >= 2:
        r0, r1 = px[0], px[-1]
        out["price_simple_return"] = (r1 / r0 - 1.0) if r0 else None
    return out


def _stats(vals: List[float]) -> Dict[str, Optional[float]]:
    if not vals:
        return {"min": None, "max": None, "mean": None, "stdev": None}
    st = None
    if len(vals) >= 2:
        try:
            st = statistics.stdev(vals)
        except statistics.StatisticsError:
            st = None
    return {
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.mean(vals),
        "stdev": round(st, 12) if st is not None and not math.isnan(st) else None,
    }


def main() -> int:
    ws = _workspace_root()
    parser = argparse.ArgumentParser(description="Binance USD-M deriv factor panel (public API, read-only).")
    parser.add_argument("--symbol", default="BTCUSDT", help="USDT-M perpetual symbol")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Futures REST base URL")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ws / "reports",
        help="Output directory (default: workspace reports/)",
    )
    parser.add_argument("--samples", type=int, default=1, help="Number of snapshots (>=1)")
    parser.add_argument("--interval-sec", type=float, default=5.0, help="Sleep between samples")
    parser.add_argument("--state-file", type=Path, default=None, help="OI delta continuity file")
    parser.add_argument("--no-state", action="store_true", help="Do not read/write OI state file")
    args = parser.parse_args()

    if args.samples < 1:
        print("--samples must be >= 1", file=sys.stderr)
        return 1

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.state_file or (out_dir / STATE_NAME)

    prev_oi: Optional[float] = None
    if not args.no_state:
        st = load_state(state_path)
        if st and str(st.get("symbol", "")).upper() == args.symbol.upper():
            prev_oi = _maybe_float(st.get("last_open_interest_base"))

    rows: List[PanelRow] = []
    try:
        for i in range(args.samples):
            row = build_row(args.symbol.upper(), i, prev_oi, args.base_url.rstrip("/"))
            rows.append(row)
            d = asdict(row)
            line = json.dumps(d, ensure_ascii=False)
            rows_path = out_dir / ROWS_NAME
            with rows_path.open("a", encoding="utf-8") as fp:
                fp.write(line + "\n")
            if row.open_interest_base is not None:
                prev_oi = row.open_interest_base
            if i < args.samples - 1 and args.interval_sec > 0:
                time.sleep(args.interval_sec)
    except Exception as e:
        print(f"build_deriv_factor_panel_v1 failed: {e}", file=sys.stderr)
        return 2

    if not args.no_state and prev_oi is not None:
        save_state(state_path, args.symbol.upper(), prev_oi, _utc_now_iso())

    summary_path = out_dir / SUMMARY_NAME
    summary_path.write_text(json.dumps(summarize(rows), indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "rows": len(rows), "rows_path": str(out_dir / ROWS_NAME), "summary_path": str(summary_path)}, indent=2))
    return 0


def _maybe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
