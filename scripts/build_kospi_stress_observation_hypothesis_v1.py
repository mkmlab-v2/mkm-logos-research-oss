#!/usr/bin/env python3
"""KOSPI B-track temporary stress observation (vol + monthly flow proxy).

Writes docs/final/artifacts/kospi_stress_observation_hypothesis_v1_latest.json.
Optional append-only log line for monitoring (default under reports/).

- observation_only / [HYPO]: not a trade signal; not merged with Track A.
- Vol: 5-trading-day stdev of log(Close) returns from kospi_daily_external_yf.csv.
- Flow: latest row of kospi_monthly_flow_external.csv (monthly cadence; not intraday 수급).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "kospi_stress_observation_hypothesis_v1"


def _rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "kospi_stress_observation_hypothesis_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_FLOW = ROOT / "research" / "market_data" / "kospi_monthly_flow_external.csv"
DEFAULT_LOG = ROOT / "reports" / "kospi_stress_observation_hypothesis_v1_log.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_kospi_closes(path: Path) -> tuple[list[str], list[float]]:
    if not path.is_file():
        return [], []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return [], []
    r = csv.DictReader(lines)
    if not r.fieldnames or "Date" not in r.fieldnames or "Close" not in r.fieldnames:
        return [], []
    dates: list[str] = []
    closes: list[float] = []
    for row in r:
        d = (row.get("Date") or "").strip()[:10]
        raw = (row.get("Close") or "").strip()
        if not d or not raw:
            continue
        try:
            c = float(raw)
        except ValueError:
            continue
        dates.append(d)
        closes.append(c)
    return dates, closes


def _log_returns(closes: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(closes)):
        prev, cur = closes[i - 1], closes[i]
        if prev <= 0 or cur <= 0:
            continue
        out.append(math.log(cur / prev))
    return out


def _latest_monthly_flow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "reason": "missing_flow_csv"}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return {"ok": False, "reason": "empty_flow_csv"}
    r = csv.DictReader(lines)
    rows: list[dict[str, str]] = [dict(x) for x in r]
    if not rows:
        return {"ok": False, "reason": "no_flow_rows"}

    def ym_key(row: dict[str, str]) -> str:
        return (row.get("ym") or "").strip()

    rows.sort(key=ym_key, reverse=True)
    last = rows[0]
    ym = ym_key(last)

    def ffloat(k: str) -> float | None:
        v = (last.get(k) or "").strip()
        if v == "":
            return None
        try:
            return float(v)
        except ValueError:
            return None

    fn = ffloat("foreign_net_buy")
    inst = ffloat("institution_net_buy")
    return {
        "ok": True,
        "ym": ym or None,
        "foreign_net_buy_ekr_bil": fn,
        "institution_net_buy_ekr_bil": inst,
    }


def build_doc(
    *,
    kospi_csv: Path,
    flow_csv: Path,
    vol_threshold: float,
    vol_window: int,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "observation_only": True,
        "ts_utc": _utc_now_iso(),
        "label": (
            "[HYPO] KOSPI stress ease observation: 5d realized vol vs threshold + "
            "latest monthly foreign_net_buy sign (proxy). research_only; not price trade signal; "
            "no Track A merge."
        ),
        "inputs": {
            "kospi_csv": _rel_to_root(kospi_csv) if kospi_csv.is_file() else str(kospi_csv),
            "flow_csv": _rel_to_root(flow_csv) if flow_csv.is_file() else str(flow_csv),
            "vol_window_trading_days": vol_window,
            "vol_stdev_threshold": vol_threshold,
        },
        "disclaimers": [
            "Monthly flow is slow-moving; it is not the same as intraday retail/foreign tape on a broker UI.",
            "composite_stress_ease_candidate is AND(vol_gate, monthly_foreign_non_negative); null if inputs missing.",
        ],
    }

    dates, closes = _load_kospi_closes(kospi_csv)
    if len(closes) < vol_window + 1:
        base["ok"] = False
        base["error"] = "insufficient_kospi_closes_for_vol_window"
        base["as_of_trade_date"] = dates[-1] if dates else None
        base["metrics"] = {"n_closes": len(closes)}
        base["gates"] = {
            "vol_stress_eased": None,
            "monthly_foreign_net_non_negative": None,
        }
        base["composite_stress_ease_candidate"] = None
        return base

    rets = _log_returns(closes)
    if len(rets) < vol_window:
        base["ok"] = False
        base["error"] = "insufficient_log_returns"
        base["as_of_trade_date"] = dates[-1]
        base["metrics"] = {"n_closes": len(closes), "n_log_returns": len(rets)}
        base["gates"] = {"vol_stress_eased": None, "monthly_foreign_net_non_negative": None}
        base["composite_stress_ease_candidate"] = None
        return base

    window = rets[-vol_window:]
    rv = statistics.stdev(window) if len(window) > 1 else 0.0
    long_win = min(20, len(rets))
    rv20 = statistics.stdev(rets[-long_win:]) if long_win > 1 else rv

    flow = _latest_monthly_flow(flow_csv)
    fn = flow.get("foreign_net_buy_ekr_bil") if flow.get("ok") else None
    monthly_nn: bool | None
    if isinstance(fn, (int, float)):
        monthly_nn = fn >= 0.0
    else:
        monthly_nn = None

    vol_eased = rv <= vol_threshold
    composite: bool | None
    if monthly_nn is None:
        composite = None
    else:
        composite = bool(vol_eased and monthly_nn)

    base["ok"] = True
    base["as_of_trade_date"] = dates[-1]
    base["metrics"] = {
        "n_closes": len(closes),
        "n_log_returns": len(rets),
        "realized_vol_5d_logret_stdev": round(rv, 6),
        "realized_vol_20d_logret_stdev": round(rv20, 6),
        "flow_monthly": flow,
    }
    base["gates"] = {
        "vol_stress_eased": vol_eased,
        "monthly_foreign_net_non_negative": monthly_nn,
    }
    base["composite_stress_ease_candidate"] = composite
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--vol-threshold", type=float, default=0.015, help="5d stdev(log returns) gate; default 1.5%% daily.")
    ap.add_argument("--vol-window", type=int, default=5, help="Trading days for realized vol.")
    ap.add_argument("--append-log", action="store_true", help="Append one JSON line to --log-jsonl.")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    doc = build_doc(
        kospi_csv=args.kospi_csv,
        flow_csv=args.flow_csv,
        vol_threshold=args.vol_threshold,
        vol_window=max(2, int(args.vol_window)),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.append_log:
        args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        args.log_jsonl.open("a", encoding="utf-8").write(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
