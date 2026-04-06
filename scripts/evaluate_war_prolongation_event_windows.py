#!/usr/bin/env python3
"""Evaluate war-prolongation hypothesis over event windows (+1/+5/+20).

Observation lane only. Produces reproducible JSON/CSV artifacts for B-Track.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_war_prolong_20260406_multileg.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "war_prolongation_window_eval_20260406.json"
DEFAULT_OUT_CSV = ROOT / "docs" / "final" / "artifacts" / "war_prolongation_window_eval_20260406.csv"
DEFAULT_REPRO = ROOT / "docs" / "final" / "artifacts" / "repro_command_war_prolongation_20260406.txt"
DEFAULT_MARKET_DIR = ROOT / "research" / "market_data"


@dataclass
class LegInput:
    instrument: str
    symbol: str
    eval_date: str
    predicted_direction: str
    neutral_bps: float


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _load_leg_inputs(score_path: Path) -> list[LegInput]:
    doc = json.loads(score_path.read_text(encoding="utf-8"))
    rows = doc.get("rows", [])
    out: list[LegInput] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append(
            LegInput(
                instrument=str(r.get("instrument") or ""),
                symbol=str(r.get("symbol") or ""),
                eval_date=str(r.get("eval_date") or ""),
                predicted_direction=str(r.get("predicted_direction") or "").lower(),
                neutral_bps=float(r.get("neutral_bps") or 5.0),
            )
        )
    return out


def _market_csv_for_leg(market_dir: Path, instrument: str) -> Path:
    return market_dir / f"{instrument}_daily_external_yf.csv"


def _close_series(csv_path: Path) -> pd.Series:
    df = pd.read_csv(csv_path)
    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError(f"Missing Date/Close columns: {csv_path}")
    s = pd.Series(df["Close"].values, index=pd.to_datetime(df["Date"]).dt.date)
    return s.sort_index()


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate war-prolongation hypothesis at +N event windows.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_JSON)
    ap.add_argument("--market-data-dir", type=Path, default=DEFAULT_MARKET_DIR)
    ap.add_argument("--horizons", type=str, default="1,5,20")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT_CSV)
    ap.add_argument("--repro-out", type=Path, default=DEFAULT_REPRO)
    args = ap.parse_args()

    if not args.score_json.is_file():
        raise SystemExit(f"Missing score json: {args.score_json}")

    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]
    if not horizons:
        raise SystemExit("No horizons provided.")

    legs = _load_leg_inputs(args.score_json)
    if not legs:
        raise SystemExit("No leg rows in score json.")

    by_leg: dict[str, pd.Series] = {}
    warnings: list[str] = []
    for leg in legs:
        csv_path = _market_csv_for_leg(args.market_data_dir, leg.instrument)
        if not csv_path.is_file():
            warnings.append(f"missing_csv:{leg.instrument}:{csv_path}")
            continue
        by_leg[leg.instrument] = _close_series(csv_path)

    rows: list[dict] = []
    for leg in legs:
        s = by_leg.get(leg.instrument)
        if s is None:
            continue
        try:
            d0 = datetime.strptime(leg.eval_date, "%Y-%m-%d").date()
        except ValueError:
            warnings.append(f"bad_eval_date:{leg.instrument}:{leg.eval_date}")
            continue
        if d0 not in s.index:
            warnings.append(f"eval_date_not_found:{leg.instrument}:{leg.eval_date}")
            continue
        idx = list(s.index).index(d0)
        for h in horizons:
            mode = "forward"
            if idx + h < len(s.index):
                c0 = float(s.iloc[idx])
                c1 = float(s.iloc[idx + h])
                if c0 == 0:
                    warnings.append(f"zero_close:{leg.instrument}:h{h}")
                    continue
                ret = (c1 - c0) / c0
            elif idx - h >= 0:
                # Fallback when future bars are unavailable for very recent events.
                mode = "trailing_proxy"
                c0 = float(s.iloc[idx - h])
                c1 = float(s.iloc[idx])
                if c0 == 0:
                    warnings.append(f"zero_close_trailing:{leg.instrument}:h{h}")
                    continue
                ret = (c1 - c0) / c0
                warnings.append(f"fallback_trailing_proxy:{leg.instrument}:h{h}")
            else:
                warnings.append(f"horizon_oob:{leg.instrument}:h{h}")
                continue

            actual = _actual_direction(ret, leg.neutral_bps)
            hit = int(actual == leg.predicted_direction)
            rows.append(
                {
                    "instrument": leg.instrument,
                    "symbol": leg.symbol,
                    "eval_date": leg.eval_date,
                    "horizon_days": h,
                    "window_mode": mode,
                    "predicted_direction": leg.predicted_direction,
                    "actual_direction": actual,
                    "window_return": round(ret, 8),
                    "hit": hit,
                }
            )

    summary: dict[str, dict] = {}
    for h in horizons:
        sub = [r for r in rows if r["horizon_days"] == h]
        n = len(sub)
        hits = sum(r["hit"] for r in sub)
        summary[f"h{h}"] = {
            "n_evaluated": n,
            "hits": hits,
            "hit_rate": round(hits / n, 6) if n > 0 else None,
        }

    payload = {
        "schema": "war_prolongation_window_eval_v1",
        "generated_at_utc": _utc_now(),
        "score_json": str(args.score_json).replace("\\", "/"),
        "market_data_dir": str(args.market_data_dir).replace("\\", "/"),
        "horizons": horizons,
        "summary_by_horizon": summary,
        "rows": rows,
        "warnings": warnings,
        "notes": ["Observation lane only. Not for live trading promotion."],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "instrument",
                "symbol",
                "eval_date",
                "horizon_days",
                "window_mode",
                "predicted_direction",
                "actual_direction",
                "window_return",
                "hit",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    repro_cmd = (
        f'py "{(ROOT / "scripts" / "evaluate_war_prolongation_event_windows.py").as_posix()}" '
        f'--score-json "{args.score_json.as_posix()}" --market-data-dir "{args.market_data_dir.as_posix()}" '
        f'--horizons "{args.horizons}" --output-json "{args.output_json.as_posix()}" '
        f'--output-csv "{args.output_csv.as_posix()}" --repro-out "{args.repro_out.as_posix()}"'
    )
    args.repro_out.write_text(repro_cmd + "\n", encoding="utf-8")

    print(f"WROTE: {args.output_json}")
    print(f"WROTE: {args.output_csv}")
    print(f"WROTE: {args.repro_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

