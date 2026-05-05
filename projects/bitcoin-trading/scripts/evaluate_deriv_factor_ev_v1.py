#!/usr/bin/env python3
"""
evaluate_deriv_factor_ev_v1 — 파생 팩터 패널의 조건부 EV 평가기 (연구/측정 전용)

입력:
  - reports/deriv_factor_panel_rows_v1.jsonl (build_deriv_factor_panel_v1 출력)

출력:
  - reports/deriv_factor_ev_report_v1.json

주의:
  - 실매매/게이트 연동 없음 (Fact-Lock 측정 레이어).
  - 이벤트 규칙은 고정 임계치가 아니라 표본 내 분위수 기반(기본 q10/q90).
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _workspace_root() -> Path:
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


@dataclass
class Row:
    ts_sec: float
    symbol: str
    price: float
    funding_rate: Optional[float]
    oi_delta_pct: Optional[float]


def _parse_iso_to_ts(iso_text: str) -> Optional[float]:
    if not iso_text:
        return None
    try:
        # 2026-05-04T...+00:00 format
        return datetime.fromisoformat(iso_text).timestamp()
    except ValueError:
        return None


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_rows(path: Path, symbol: Optional[str]) -> List[Row]:
    rows: List[Row] = []
    if not path.is_file():
        return rows

    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            sym = str(obj.get("symbol") or "").upper()
            if symbol and sym != symbol.upper():
                continue
            ts = _parse_iso_to_ts(str(obj.get("collected_at_utc") or ""))
            price = _to_float(obj.get("price_last"))
            if price is None:
                price = _to_float(obj.get("mark_price"))
            if ts is None or price is None or price <= 0:
                continue
            rows.append(
                Row(
                    ts_sec=ts,
                    symbol=sym,
                    price=price,
                    funding_rate=_to_float(obj.get("last_funding_rate")),
                    oi_delta_pct=_to_float(obj.get("oi_delta_pct")),
                )
            )
    rows.sort(key=lambda x: x.ts_sec)
    return rows


def quantile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    q = max(0.0, min(1.0, q))
    pos = q * (len(s) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return s[lo]
    w = pos - lo
    return s[lo] * (1.0 - w) + s[hi] * w


def forward_return(rows: List[Row], idx: int, horizon_sec: int) -> Optional[float]:
    t_target = rows[idx].ts_sec + horizon_sec
    times = [r.ts_sec for r in rows]
    j = bisect.bisect_left(times, t_target)
    if j >= len(rows):
        return None
    p0 = rows[idx].price
    p1 = rows[j].price
    if p0 <= 0:
        return None
    return (p1 / p0) - 1.0


def _stats(arr: List[float]) -> Dict[str, Optional[float]]:
    if not arr:
        return {"count": 0, "mean": None, "median": None, "stdev": None, "win_rate": None}
    mean_v = statistics.mean(arr)
    med_v = statistics.median(arr)
    stdev_v = statistics.stdev(arr) if len(arr) >= 2 else None
    win = sum(1 for x in arr if x > 0.0) / len(arr)
    return {
        "count": len(arr),
        "mean": mean_v,
        "median": med_v,
        "stdev": stdev_v,
        "win_rate": win,
    }


def evaluate(rows: List[Row], horizons_sec: List[int], roundtrip_cost_bps: float) -> Dict[str, Any]:
    funding_vals = [r.funding_rate for r in rows if r.funding_rate is not None]
    oi_vals = [r.oi_delta_pct for r in rows if r.oi_delta_pct is not None]

    q10_f = quantile(funding_vals, 0.10)
    q90_f = quantile(funding_vals, 0.90)
    q10_oi = quantile(oi_vals, 0.10)
    q90_oi = quantile(oi_vals, 0.90)
    cost = roundtrip_cost_bps / 10000.0

    events = [
        ("funding_low", lambda r: q10_f is not None and r.funding_rate is not None and r.funding_rate <= q10_f),
        ("funding_high", lambda r: q90_f is not None and r.funding_rate is not None and r.funding_rate >= q90_f),
        ("oi_spike_up", lambda r: q90_oi is not None and r.oi_delta_pct is not None and r.oi_delta_pct >= q90_oi),
        ("oi_spike_down", lambda r: q10_oi is not None and r.oi_delta_pct is not None and r.oi_delta_pct <= q10_oi),
        (
            "combo_short_squeeze_like",
            lambda r: (
                q10_f is not None
                and q90_oi is not None
                and r.funding_rate is not None
                and r.oi_delta_pct is not None
                and r.funding_rate <= q10_f
                and r.oi_delta_pct >= q90_oi
            ),
        ),
        (
            "combo_long_flush_like",
            lambda r: (
                q90_f is not None
                and q10_oi is not None
                and r.funding_rate is not None
                and r.oi_delta_pct is not None
                and r.funding_rate >= q90_f
                and r.oi_delta_pct <= q10_oi
            ),
        ),
    ]

    report: Dict[str, Any] = {
        "schema": "deriv_factor_ev_report_v1",
        "row_count": len(rows),
        "symbol": rows[0].symbol if rows else None,
        "thresholds": {
            "funding_q10": q10_f,
            "funding_q90": q90_f,
            "oi_delta_pct_q10": q10_oi,
            "oi_delta_pct_q90": q90_oi,
        },
        "roundtrip_cost_bps": roundtrip_cost_bps,
        "horizons_sec": horizons_sec,
        "events": {},
    }

    for name, pred in events:
        hit_indices = [i for i, r in enumerate(rows) if pred(r)]
        event_payload: Dict[str, Any] = {
            "event_count": len(hit_indices),
            "horizon_eval": {},
        }
        for h in horizons_sec:
            raw_rets: List[float] = []
            net_rets: List[float] = []
            for i in hit_indices:
                fr = forward_return(rows, i, h)
                if fr is None:
                    continue
                raw_rets.append(fr)
                net_rets.append(fr - cost)
            event_payload["horizon_eval"][str(h)] = {
                "raw": _stats(raw_rets),
                "net_after_cost": _stats(net_rets),
                "mean_bps_raw": (statistics.mean(raw_rets) * 10000.0) if raw_rets else None,
                "mean_bps_net": (statistics.mean(net_rets) * 10000.0) if net_rets else None,
            }
        report["events"][name] = event_payload
    return report


def parse_horizons(raw: str) -> List[int]:
    out: List[int] = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            v = int(tok)
        except ValueError as e:
            raise ValueError(f"invalid horizon token: {tok}") from e
        if v <= 0:
            raise ValueError("horizon must be positive seconds")
        out.append(v)
    if not out:
        raise ValueError("at least one horizon required")
    return out


def main() -> int:
    ws = _workspace_root()
    parser = argparse.ArgumentParser(description="Evaluate conditional EV from deriv factor panel rows.")
    parser.add_argument(
        "--rows-jsonl",
        type=Path,
        default=ws / "reports" / "deriv_factor_panel_rows_v1.jsonl",
        help="Input panel rows JSONL path",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ws / "reports" / "deriv_factor_ev_report_v1.json",
        help="Output report JSON path",
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Symbol filter")
    parser.add_argument(
        "--horizons-sec",
        default="300,900,3600",
        help="Comma-separated forward horizons in seconds (e.g. 300,900,3600)",
    )
    parser.add_argument(
        "--roundtrip-cost-bps",
        type=float,
        default=6.0,
        help="Roundtrip transaction cost in bps for net EV",
    )
    args = parser.parse_args()

    horizons = parse_horizons(args.horizons_sec)
    rows = load_rows(args.rows_jsonl, args.symbol)
    report = evaluate(rows, horizons, args.roundtrip_cost_bps)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "rows": report["row_count"],
                "symbol": report["symbol"],
                "report": str(args.out_json),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
