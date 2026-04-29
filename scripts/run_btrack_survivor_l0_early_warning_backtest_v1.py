# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.7}
# Balance: 90
# Purpose: L0 early-warning backtest using crash-onset labels from survivor resonance.
# Keywords: btrack, survivor, l0, early-warning, crash-onset, correlation
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_KNOWLEDGE_REPORT_JSON = ART / "bible_meaning_knowledge_ip_report_latest.json"
DEFAULT_CANDIDATES_JSON = ART / "bible_meaning_insight_candidates_latest.json"
DEFAULT_RESONANCE_JSONL = ART / "global_atom_survivor_resonance_daily_real_latest.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUTPUT_JSON = ART / "btrack_survivor_l0_early_warning_backtest_latest.json"


@dataclass
class CorrResult:
    n: int
    pearson: float | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _extract_survivor_ids(knowledge_report: dict[str, Any], candidates_doc: dict[str, Any]) -> set[str]:
    candidates = candidates_doc.get("candidates") if isinstance(candidates_doc.get("candidates"), list) else []
    if not candidates:
        return set()
    survivor_count = int(((knowledge_report.get("summary") or {}).get("survivor_count")) or 5)
    explicit_ids = knowledge_report.get("survivor_ids")
    if isinstance(explicit_ids, list) and explicit_ids:
        return {str(x) for x in explicit_ids if x}
    ranked = sorted(
        [c for c in candidates if isinstance(c, dict)],
        key=lambda c: (
            _safe_float(c.get("hub_score")) or 0.0,
            _safe_float(c.get("path_score")) or 0.0,
            _safe_float(c.get("cluster_size")) or 0.0,
        ),
        reverse=True,
    )
    return {str(x.get("candidate_id")) for x in ranked[:survivor_count] if x.get("candidate_id")}


def _load_market_close_series(csv_path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not csv_path.is_file():
        return out
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = (row.get("Date") or row.get("date") or "").strip()
            close_v = _safe_float(row.get("Close") or row.get("close"))
            if d and close_v is not None:
                out[d] = close_v
    return out


def _market_crash_flags(close_by_date: dict[str, float], crash_dd_threshold: float) -> dict[str, float]:
    dates = sorted(close_by_date.keys())
    out: dict[str, float] = {}
    peak = float("-inf")
    for d in dates:
        close = close_by_date[d]
        peak = max(peak, close)
        drawdown = (close / peak - 1.0) if peak > 0 else 0.0
        out[d] = 1.0 if drawdown <= crash_dd_threshold else 0.0
    return out


def _build_crash_onset_labels(crash_flag_by_date: dict[str, float], horizon_days: int) -> dict[str, float]:
    dates = sorted(crash_flag_by_date.keys())
    out: dict[str, float] = {}
    for i, d in enumerate(dates):
        curr = crash_flag_by_date[d]
        if curr >= 0.5:
            out[d] = 0.0
            continue
        upper = min(len(dates), i + 1 + max(1, horizon_days))
        future = dates[i + 1 : upper]
        out[d] = 1.0 if any(crash_flag_by_date[x] >= 0.5 for x in future) else 0.0
    return out


def _aggregate_resonance_by_date(rows: list[dict[str, Any]], survivor_ids: set[str]) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for r in rows:
        symbol_id = str(r.get("symbol_id") or r.get("candidate_id") or "").strip()
        if symbol_id not in survivor_ids:
            continue
        d = str(r.get("date") or r.get("eval_date") or "").strip()
        score = _safe_float(r.get("resonance_score"))
        if score is None:
            score = _safe_float(r.get("resonance"))
        if not d or score is None:
            continue
        acc.setdefault(d, []).append(score)
    return {d: (sum(v) / len(v)) for d, v in acc.items() if v}


def _pearson(x: list[float], y: list[float]) -> CorrResult:
    n = min(len(x), len(y))
    if n < 3:
        return CorrResult(n=n, pearson=None)
    mx = sum(x) / n
    my = sum(y) / n
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx <= 0 or vy <= 0:
        return CorrResult(n=n, pearson=None)
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    return CorrResult(n=n, pearson=cov / (vx**0.5 * vy**0.5))


def _lagged_series(signal_by_date: dict[str, float], metric_by_date: dict[str, float], lag_days: int) -> tuple[list[float], list[float]]:
    dates = sorted(set(signal_by_date.keys()) & set(metric_by_date.keys()))
    if lag_days == 0:
        return [signal_by_date[d] for d in dates], [metric_by_date[d] for d in dates]
    idx = {d: i for i, d in enumerate(dates)}
    out_x: list[float] = []
    out_y: list[float] = []
    for d in dates:
        j = idx[d] + lag_days
        if j < 0 or j >= len(dates):
            continue
        out_x.append(signal_by_date[d])
        out_y.append(metric_by_date[dates[j]])
    return out_x, out_y


def _permutation_pvalue(x: list[float], y: list[float], observed_abs_corr: float, rounds: int, seed: int) -> float | None:
    if len(x) < 8 or len(y) < 8 or rounds <= 0:
        return None
    rnd = random.Random(seed)
    yy = list(y)
    ge = 0
    for _ in range(rounds):
        rnd.shuffle(yy)
        r = _pearson(x, yy).pearson
        if r is not None and abs(r) >= observed_abs_corr:
            ge += 1
    return (ge + 1) / (rounds + 1)


def _analyze_asset(signal_by_date: dict[str, float], onset_by_date: dict[str, float], max_lag_days: int, permutation_rounds: int, seed: int) -> dict[str, Any]:
    lag_rows: list[dict[str, Any]] = []
    best_abs = -1.0
    best: dict[str, Any] | None = None
    for lag in range(-max_lag_days, max_lag_days + 1):
        xs, ys = _lagged_series(signal_by_date, onset_by_date, lag)
        corr = _pearson(xs, ys)
        row = {
            "lag_days": lag,
            "onset_corr": corr.pearson,
            "onset_n": corr.n,
        }
        lag_rows.append(row)
        c = row["onset_corr"]
        if c is not None and abs(c) > best_abs:
            best_abs = abs(c)
            best = row
    p = None
    if best is not None and best.get("onset_corr") is not None:
        xs, ys = _lagged_series(signal_by_date, onset_by_date, int(best["lag_days"]))
        p = _permutation_pvalue(xs, ys, abs(float(best["onset_corr"])), permutation_rounds, seed)
    return {
        "lags": lag_rows,
        "best_abs_onset_corr_row": best,
        "best_onset_corr_permutation_pvalue": p,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="L0 early-warning backtest for survivor resonance using crash-onset labels.")
    ap.add_argument("--knowledge-report-json", type=Path, default=DEFAULT_KNOWLEDGE_REPORT_JSON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_JSON)
    ap.add_argument("--resonance-jsonl", type=Path, default=DEFAULT_RESONANCE_JSONL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--crash-dd-threshold", type=float, default=-0.30)
    ap.add_argument("--onset-horizon-days", type=int, default=5)
    ap.add_argument("--max-lag-days", type=int, default=30)
    ap.add_argument("--permutation-rounds", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = ap.parse_args()

    knowledge = _read_json(args.knowledge_report_json)
    candidates = _read_json(args.candidates_json)
    survivor_ids = _extract_survivor_ids(knowledge, candidates)
    resonance_rows = _read_jsonl(args.resonance_jsonl)
    signal_by_date = _aggregate_resonance_by_date(resonance_rows, survivor_ids)

    kospi_flags = _market_crash_flags(_load_market_close_series(args.kospi_csv), args.crash_dd_threshold)
    btc_flags = _market_crash_flags(_load_market_close_series(args.btc_csv), args.crash_dd_threshold)
    kospi_onset = _build_crash_onset_labels(kospi_flags, args.onset_horizon_days)
    btc_onset = _build_crash_onset_labels(btc_flags, args.onset_horizon_days)

    out = {
        "schema": "btrack_survivor_l0_early_warning_backtest_v1",
        "generated_at_utc": _now_iso(),
        "research_only": True,
        "l0_warning_only": True,
        "inputs": {
            "knowledge_report_json": str(args.knowledge_report_json),
            "candidates_json": str(args.candidates_json),
            "resonance_jsonl": str(args.resonance_jsonl),
            "crash_dd_threshold": float(args.crash_dd_threshold),
            "onset_horizon_days": int(args.onset_horizon_days),
            "max_lag_days": int(args.max_lag_days),
            "permutation_rounds": int(args.permutation_rounds),
            "seed": int(args.seed),
        },
        "signal": {
            "survivor_signal_dates": len(signal_by_date),
            "survivor_signal_start_date": min(signal_by_date.keys()) if signal_by_date else None,
            "survivor_signal_end_date": max(signal_by_date.keys()) if signal_by_date else None,
        },
        "analysis": {
            "kospi": _analyze_asset(signal_by_date, kospi_onset, args.max_lag_days, args.permutation_rounds, args.seed),
            "btc": _analyze_asset(signal_by_date, btc_onset, args.max_lag_days, args.permutation_rounds, args.seed),
        },
        "interpretation_note": "L0 early-warning research metric only; not a trading trigger.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
