#!/usr/bin/env python3
"""Refresh AIDC AB summary from latest score rows (B-Track only)."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCORE_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
OUT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "ab_result_summary.json"
OUT_TS = ROOT / "docs" / "final" / "artifacts" / "ab_result_timeseries.csv"
DEFAULT_ANSWER_KEY = (
    ROOT
    / "reports"
    / "constitution"
    / "btrack_pilot"
    / "blind_replay"
    / "blind_replay_answer_key_historical_btcusdt_1d_cfg6_w60_h10_s2_seed45.jsonl"
)
DEFAULT_PREDICTION_SOURCE = (
    ROOT
    / "reports"
    / "constitution"
    / "btrack_pilot"
    / "blind_replay"
    / "blind_replay_predictions_12ai_proxy_C_latest.jsonl"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_score(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _rows_from_score(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("rows")
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return [doc]


def _wilson_95_ci(k: int, n: int) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    phat = k / n
    denom = 1.0 + (z * z) / n
    center = (phat + (z * z) / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


def _binomial_sf_geq(k: int, n: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    # Exact one-sided p-value: P[X >= k] for X~Binomial(n, p0)
    s = 0.0
    for x in range(k, n + 1):
        s += math.comb(n, x) * (p0**x) * ((1.0 - p0) ** (n - x))
    return min(max(s, 0.0), 1.0)


def _append_timeseries(path: Path, *, ts_utc: str, hit_rate: float, n: int, hits: int, p_value: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp_utc",
                "hit_rate",
                "n_evaluated",
                "hits",
                "one_sided_p_value_vs_baseline",
            ],
        )
        if write_header:
            w.writeheader()
        w.writerow(
            {
                "timestamp_utc": ts_utc,
                "hit_rate": f"{hit_rate:.6f}",
                "n_evaluated": str(n),
                "hits": str(hits),
                "one_sided_p_value_vs_baseline": f"{p_value:.6f}",
            }
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Refresh ab_result_summary.json from latest prophecy score.")
    ap.add_argument("--score-json", type=Path, default=SCORE_JSON)
    ap.add_argument("--answer-key-jsonl", type=Path, default=DEFAULT_ANSWER_KEY)
    ap.add_argument("--prediction-jsonl", type=Path, default=DEFAULT_PREDICTION_SOURCE)
    ap.add_argument("--output", type=Path, default=OUT_SUMMARY)
    ap.add_argument("--timeseries", type=Path, default=OUT_TS)
    ap.add_argument("--baseline-hit-rate", type=float, default=1.0 / 3.0)
    args = ap.parse_args()

    comparable: list[tuple[str, str]] = []
    input_meta: dict[str, Any]
    if args.answer_key_jsonl.is_file() and args.prediction_jsonl.is_file():
        answers = _load_jsonl(args.answer_key_jsonl)
        preds = _load_jsonl(args.prediction_jsonl)
        answer_map = {
            str(r.get("sample_id")): str(r.get("answer_label") or "").strip().upper()
            for r in answers
            if r.get("sample_id")
        }
        pred_map = {
            str(r.get("sample_id")): str(r.get("direction_sign") or "").strip().upper()
            for r in preds
            if r.get("sample_id")
        }
        for sid, plabel in pred_map.items():
            alabel = answer_map.get(sid)
            if plabel and alabel:
                comparable.append((plabel, alabel))
        input_meta = {
            "answer_key": str(args.answer_key_jsonl).replace("\\", "/"),
            "prediction_source": str(args.prediction_jsonl).replace("\\", "/"),
            "timeseries_csv": str(args.timeseries).replace("\\", "/"),
        }
    else:
        doc = _load_score(args.score_json)
        rows = _rows_from_score(doc)
        for r in rows:
            pd = str(r.get("predicted_direction") or "").strip().lower()
            ad = str(r.get("actual_direction") or "").strip().lower()
            if pd in ("bull", "bear", "neutral") and ad in ("bull", "bear", "neutral"):
                comparable.append((pd, ad))
        input_meta = {
            "score_json": str(args.score_json).replace("\\", "/"),
            "timeseries_csv": str(args.timeseries).replace("\\", "/"),
        }

    n = len(comparable)
    hits = sum(1 for pd, ad in comparable if pd == ad)
    hit_rate = (hits / n) if n > 0 else 0.0

    ci_lo, ci_hi = _wilson_95_ci(hits, n) if n > 0 else (0.0, 0.0)
    p0 = float(args.baseline_hit_rate)
    p_value = _binomial_sf_geq(hits, n, p0) if n > 0 else 1.0
    ts_utc = _utc_now()

    out = {
        "schema": "aidc_ab_result_summary_v1",
        "generated_at_utc": ts_utc,
        "status": "exploratory_with_stats",
        "scope": "observation_lane_blind_replay",
        "comparison": {
            "baseline": {
                "name": "A",
                "description": "Chance baseline for 3-class direction labels",
                "hit_rate_assumed": round(p0, 6),
            },
            "treatment": {
                "name": "B",
                "description": "Latest btrack_prophecy_score directional match on current eval payload",
            },
        },
        "metrics_snapshot": {
            "hit_rate": round(hit_rate, 6),
            "n_evaluated": n,
            "hits": hits,
            "miss": max(0, n - hits),
        },
        "statistical_test": {
            "method": "Wilson 95% CI + one-sided exact binomial test vs chance baseline",
            "confidence_interval_95": [round(ci_lo, 6), round(ci_hi, 6)],
            "one_sided_p_value_vs_baseline": round(p_value, 6),
            "uplift_vs_baseline": round(hit_rate - p0, 6),
        },
        "inputs": input_meta,
        "limitations": [
            "Exploratory lane only; not linked to live trading.",
            "Current snapshot may be low-N if score payload has few rows.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_timeseries(args.timeseries, ts_utc=ts_utc, hit_rate=hit_rate, n=n, hits=hits, p_value=p_value)
    print(f"WROTE: {args.output}")
    print(f"AB: n={n} hits={hits} hit_rate={hit_rate:.6f} p_value={p_value:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
