# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.5, M:0.7}
# Balance: 90
# Purpose: Extract survivor symbols and backtest resonance correlation vs crash windows.
# Keywords: btrack, survivor, correlation, drawdown, crash, logos
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
DEFAULT_RESONANCE_JSONL = ART / "global_atom_survivor_resonance_daily_latest.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUTPUT_JSON = ART / "btrack_survivor_crash_correlation_backtest_latest.json"


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
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _extract_survivors(knowledge_report: dict[str, Any], candidates_doc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    candidates = candidates_doc.get("candidates") if isinstance(candidates_doc.get("candidates"), list) else []
    if not candidates:
        return [], ["no_candidates_found"]
    survivor_count = int(((knowledge_report.get("summary") or {}).get("survivor_count")) or 0)
    if survivor_count <= 0:
        survivor_count = 5
        warnings.append("survivor_count_missing_defaulted_to_5")

    explicit_ids = knowledge_report.get("survivor_ids")
    explicit = knowledge_report.get("survivors")
    survivor_ids: set[str] = set()
    if isinstance(explicit_ids, list):
        survivor_ids |= {str(x) for x in explicit_ids if x}
    if isinstance(explicit, list):
        for x in explicit:
            if isinstance(x, dict):
                cid = x.get("candidate_id")
                if cid:
                    survivor_ids.add(str(cid))
            elif x:
                survivor_ids.add(str(x))
    if survivor_ids:
        chosen = [c for c in candidates if str(c.get("candidate_id")) in survivor_ids]
        if chosen:
            return chosen[:survivor_count], warnings
        warnings.append("explicit_survivors_not_matched_in_candidates_fallback_rank")

    ranked = sorted(
        [c for c in candidates if isinstance(c, dict)],
        key=lambda c: (
            _safe_float(c.get("hub_score")) or 0.0,
            _safe_float(c.get("path_score")) or 0.0,
            _safe_float(c.get("cluster_size")) or 0.0,
        ),
        reverse=True,
    )
    warnings.append("survivors_inferred_from_candidate_ranking")
    return ranked[:survivor_count], warnings


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


def _market_features(close_by_date: dict[str, float], crash_dd_threshold: float) -> dict[str, dict[str, float]]:
    dates = sorted(close_by_date.keys())
    if not dates:
        return {}
    res: dict[str, dict[str, float]] = {}
    peak = float("-inf")
    prev_close: float | None = None
    for d in dates:
        close = close_by_date[d]
        peak = max(peak, close)
        drawdown = (close / peak - 1.0) if peak > 0 else 0.0
        daily_ret = 0.0 if prev_close is None or prev_close == 0 else (close / prev_close - 1.0)
        res[d] = {
            "daily_return": daily_ret,
            "drawdown": drawdown,
            "crash_flag": 1.0 if drawdown <= crash_dd_threshold else 0.0,
        }
        prev_close = close
    return res


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
    return {d: (sum(vals) / len(vals)) for d, vals in acc.items() if vals}


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
        d2 = dates[j]
        out_x.append(signal_by_date[d])
        out_y.append(metric_by_date[d2])
    return out_x, out_y


def _permutation_pvalue(x: list[float], y: list[float], observed_abs_corr: float, rounds: int, seed: int) -> float | None:
    if len(x) < 8 or len(y) < 8 or rounds <= 0:
        return None
    rnd = random.Random(seed)
    greater_or_equal = 0
    yy = list(y)
    for _ in range(rounds):
        rnd.shuffle(yy)
        r = _pearson(x, yy).pearson
        if r is None:
            continue
        if abs(r) >= observed_abs_corr:
            greater_or_equal += 1
    return (greater_or_equal + 1) / (rounds + 1)


def _analyze_asset(
    signal_by_date: dict[str, float],
    market_feature_by_date: dict[str, dict[str, float]],
    max_lag_days: int,
    permutation_rounds: int,
    seed: int,
) -> dict[str, Any]:
    daily_ret = {d: v["daily_return"] for d, v in market_feature_by_date.items()}
    crash = {d: v["crash_flag"] for d, v in market_feature_by_date.items()}
    lag_results: list[dict[str, Any]] = []
    best_abs = -1.0
    best_row: dict[str, Any] | None = None

    for lag in range(-max_lag_days, max_lag_days + 1):
        xs_ret, ys_ret = _lagged_series(signal_by_date, daily_ret, lag)
        ret_corr = _pearson(xs_ret, ys_ret)
        xs_cr, ys_cr = _lagged_series(signal_by_date, crash, lag)
        crash_corr = _pearson(xs_cr, ys_cr)
        row = {
            "lag_days": lag,
            "return_corr": ret_corr.pearson,
            "return_n": ret_corr.n,
            "crash_flag_corr": crash_corr.pearson,
            "crash_flag_n": crash_corr.n,
        }
        lag_results.append(row)
        for k in ("return_corr", "crash_flag_corr"):
            c = row[k]
            if c is not None and abs(c) > best_abs:
                best_abs = abs(c)
                best_row = row

    p_value = None
    if best_row is not None:
        lag = int(best_row["lag_days"])
        xs_ret, ys_ret = _lagged_series(signal_by_date, daily_ret, lag)
        corr_abs = abs(float(best_row.get("return_corr") or 0.0))
        p_value = _permutation_pvalue(xs_ret, ys_ret, corr_abs, permutation_rounds, seed)

    return {
        "lags": lag_results,
        "best_abs_corr_row": best_row,
        "best_return_corr_permutation_pvalue": p_value,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Backtest survivor-symbol resonance correlation vs KOSPI/BTC crash windows.")
    ap.add_argument("--knowledge-report-json", type=Path, default=DEFAULT_KNOWLEDGE_REPORT_JSON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_JSON)
    ap.add_argument("--resonance-jsonl", type=Path, default=DEFAULT_RESONANCE_JSONL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--crash-dd-threshold", type=float, default=-0.30, help="Crash flag threshold by drawdown (e.g. -0.30).")
    ap.add_argument("--max-lag-days", type=int, default=30)
    ap.add_argument("--permutation-rounds", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = ap.parse_args()

    knowledge = _read_json(args.knowledge_report_json)
    candidates = _read_json(args.candidates_json)
    survivors, survivor_warnings = _extract_survivors(knowledge, candidates)
    survivor_ids = {str(x.get("candidate_id")) for x in survivors if isinstance(x, dict)}

    resonance_rows = _read_jsonl(args.resonance_jsonl)
    signal_by_date = _aggregate_resonance_by_date(resonance_rows, survivor_ids)

    kospi_features = _market_features(_load_market_close_series(args.kospi_csv), args.crash_dd_threshold)
    btc_features = _market_features(_load_market_close_series(args.btc_csv), args.crash_dd_threshold)

    warnings: list[str] = list(survivor_warnings)
    if not resonance_rows:
        warnings.append("resonance_jsonl_missing_or_empty")
    if not signal_by_date:
        warnings.append("no_survivor_resonance_signal_after_filter")
    if not kospi_features:
        warnings.append("kospi_csv_missing_or_empty")
    if not btc_features:
        warnings.append("btc_csv_missing_or_empty")

    result = {
        "schema": "btrack_survivor_crash_correlation_backtest_v1",
        "generated_at_utc": _now_iso(),
        "research_only": True,
        "hypothesis_tag": "[HYPO-3]",
        "inputs": {
            "knowledge_report_json": str(args.knowledge_report_json),
            "candidates_json": str(args.candidates_json),
            "resonance_jsonl": str(args.resonance_jsonl),
            "kospi_csv": str(args.kospi_csv),
            "btc_csv": str(args.btc_csv),
            "crash_dd_threshold": float(args.crash_dd_threshold),
            "max_lag_days": int(args.max_lag_days),
            "permutation_rounds": int(args.permutation_rounds),
            "seed": int(args.seed),
        },
        "survivors": [
            {
                "candidate_id": s.get("candidate_id"),
                "source_node_id": s.get("source_node_id"),
                "hub_score": s.get("hub_score"),
                "path_score": s.get("path_score"),
                "cluster_size": s.get("cluster_size"),
                "regime_tag": s.get("regime_tag"),
            }
            for s in survivors
        ],
        "signal": {
            "survivor_signal_dates": len(signal_by_date),
            "survivor_signal_start_date": min(signal_by_date.keys()) if signal_by_date else None,
            "survivor_signal_end_date": max(signal_by_date.keys()) if signal_by_date else None,
        },
        "analysis": {
            "kospi": _analyze_asset(signal_by_date, kospi_features, args.max_lag_days, args.permutation_rounds, args.seed),
            "btc": _analyze_asset(signal_by_date, btc_features, args.max_lag_days, args.permutation_rounds, args.seed),
        },
        "warnings": warnings,
        "interpretation_note": "Correlation is observational and non-causal. Do not use for A-track trading trigger.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(f"survivor_count={len(result['survivors'])} signal_dates={result['signal']['survivor_signal_dates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
