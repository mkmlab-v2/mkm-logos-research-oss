#!/usr/bin/env python3
"""[HYPO] Compare frozen batch vs per-date combo on the same score panel window.

Does not mutate Track A artifacts. Writes reports/frozen_vs_per_date_panel_compare_v1_latest.json.

Modes:
  frozen — rows as scored today (frozen_single_direction_batch).
  blocked_wf_oos — blocked walk-forward test blocks only (same grid as promotion WF).
  expanding_oos — each eval_date: fit on strictly prior dates, predict that date (full panel).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/frozen_vs_per_date_panel_compare_v1_latest.json"
SCHEMA = "frozen_vs_per_date_panel_compare_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _leg_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Match eval_prophecy_hit_rate_v1 all-rows headline metrics for btc rows."""
    hits = 0
    n = 0
    n_neutral_pred = 0
    dir_hits = 0
    n_dir_calls = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").strip().lower()
        actual = str(r.get("actual_direction") or "").strip().lower()
        if not pred or not actual:
            continue
        n += 1
        if pred == actual:
            hits += 1
        if pred == "neutral":
            n_neutral_pred += 1
        else:
            n_dir_calls += 1
            if pred == actual:
                dir_hits += 1
    rate = (hits / n) if n else None
    dir_rate = (dir_hits / n_dir_calls) if n_dir_calls else None
    return {
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "n_neutral_predictions": n_neutral_pred,
        "price_hit_rate_on_directional_calls": round(dir_rate, 6) if dir_rate is not None else None,
        "n_directional_calls": n_dir_calls,
        "directional_call_hits": dir_hits,
    }


def _load_wf_module():
    path = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"
    spec = importlib.util.spec_from_file_location("prophecy_per_date_combo_wf", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _btc_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = sorted(
        [
            r
            for r in (doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == "btc"
        ],
        key=lambda r: str(r.get("eval_date")),
    )
    return rows


def _frozen_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    m = _leg_metrics(rows)
    m["scoring_mode"] = "frozen_single_direction_batch"
    frozen = str(rows[0].get("predicted_direction") or "").strip().lower() if rows else None
    m["frozen_direction"] = frozen
    return m


def _blocked_wf_oos(
    wf,
    rows: list[dict[str, Any]],
    km: dict,
    bm: dict,
    kf: dict,
    bf: dict,
    *,
    n_folds: int,
    train_objective: str,
    include_source: bool,
    include_expanded: bool,
) -> dict[str, Any]:
    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    n_eff = max(2, min(n_folds, len(dates)))
    fold_specs = wf._blocked_walkforward_folds(dates, n_eff)
    oos_rows: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set, test_set = set(train_dates), set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        fitted = wf._best_params_on_train(
            train,
            km,
            bm,
            kf,
            bf,
            train_objective=train_objective,
            include_source_direction_signal=include_source,
            include_expanded_prior_features=include_expanded,
        )
        if fitted is None:
            continue
        _, params = fitted
        for r in test:
            pred = wf._predict(
                r,
                params,
                km,
                bm,
                kf,
                bf,
                include_source_direction_signal=include_source,
                include_expanded_prior_features=include_expanded,
            )
            oos_rows.append({**r, "predicted_direction": pred, "oos_method": "blocked_wf"})
        test_acc, test_hits = wf._acc(
            test,
            params,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=include_source,
            include_expanded_prior_features=include_expanded,
        )
        fold_summaries.append(
            {
                "fold_index": fi,
                "n_test": len(test),
                "test_accuracy": round(test_acc, 6),
                "test_hits": test_hits,
                "test_dates_first": test_dates[0] if test_dates else None,
                "test_dates_last": test_dates[-1] if test_dates else None,
            }
        )
    m = _leg_metrics(oos_rows)
    m["scoring_mode"] = "per_date_blocked_walkforward_oos"
    m["n_oos_dates"] = len(oos_rows)
    m["n_panel_dates"] = len(dates)
    m["dates_not_in_oos"] = sorted(set(dates) - {str(r.get("eval_date"))[:10] for r in oos_rows})
    m["folds"] = fold_summaries
    return m


def _expanding_oos(
    wf,
    rows: list[dict[str, Any]],
    km: dict,
    bm: dict,
    kf: dict,
    bf: dict,
    *,
    min_train_rows: int,
    train_objective: str,
    include_source: bool,
    include_expanded: bool,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    oos_rows: list[dict[str, Any]] = []
    direction_map: list[dict[str, str]] = []
    for i in range(min_train_rows, len(rows)):
        train = rows[:i]
        row = rows[i]
        fitted = wf._best_params_on_train(
            train,
            km,
            bm,
            kf,
            bf,
            train_objective=train_objective,
            include_source_direction_signal=include_source,
            include_expanded_prior_features=include_expanded,
        )
        if fitted is None:
            continue
        _, params = fitted
        pred = wf._predict(
            row,
            params,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=include_source,
            include_expanded_prior_features=include_expanded,
        )
        oos_rows.append({**row, "predicted_direction": pred, "oos_method": "expanding"})
        direction_map.append(
            {"eval_date": str(row.get("eval_date"))[:10], "predicted_direction": pred}
        )
    m = _leg_metrics(oos_rows)
    m["scoring_mode"] = "per_date_expanding_walkforward_oos"
    m["n_oos_dates"] = len(oos_rows)
    m["n_panel_dates"] = len(rows)
    m["min_train_rows"] = min_train_rows
    m["warmup_dates_excluded"] = [str(rows[j].get("eval_date"))[:10] for j in range(min_train_rows)]
    return m, direction_map


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--n-folds", type=int, default=3, help="Blocked WF fold count (promotion default).")
    ap.add_argument("--min-train-rows", type=int, default=10, help="Expanding OOS: skip first N dates.")
    ap.add_argument(
        "--train-objective",
        choices=("accuracy", "margin_vs_bull"),
        default="accuracy",
        help="Match promotion WF artifact (accuracy) unless overridden.",
    )
    ap.add_argument("--include-source-direction-signal", action="store_true", default=True)
    ap.add_argument("--no-include-source-direction-signal", action="store_false", dest="include_source_direction_signal")
    ap.add_argument("--include-expanded-prior-features", action="store_true", default=True)
    ap.add_argument("--no-include-expanded-prior-features", action="store_false", dest="include_expanded_prior_features")
    ap.add_argument(
        "--run-scored-eval",
        action="store_true",
        help="Write per-date JSON + rebuild score + eval_prophecy_hit_rate (temp under reports/).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = _load_json(args.score_json)
    if not doc:
        raise SystemExit(f"missing score json: {args.score_json}")
    rows = _btc_rows(doc)
    if not rows:
        raise SystemExit("no btc rows in score panel")

    wf = _load_wf_module()
    km = wf._prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = wf._prior_map(args.btc_csv) if args.btc_csv.is_file() else {}
    kf = wf._feature_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bf = wf._feature_map(args.btc_csv) if args.btc_csv.is_file() else {}

    frozen_m = _frozen_metrics(rows)
    blocked_m = _blocked_wf_oos(
        wf,
        rows,
        km,
        bm,
        kf,
        bf,
        n_folds=args.n_folds,
        train_objective=args.train_objective,
        include_source=args.include_source_direction_signal,
        include_expanded=args.include_expanded_prior_features,
    )
    expanding_m, dir_map = _expanding_oos(
        wf,
        rows,
        km,
        bm,
        kf,
        bf,
        min_train_rows=args.min_train_rows,
        train_objective=args.train_objective,
        include_source=args.include_source_direction_signal,
        include_expanded=args.include_expanded_prior_features,
    )

    def _delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(b - a, 6)

    frozen_rate = frozen_m.get("price_directional_hit_rate")
    blocked_rate = blocked_m.get("price_directional_hit_rate")
    expanding_rate = expanding_m.get("price_directional_hit_rate")

    scored_eval: dict[str, Any] | None = None
    if args.run_scored_eval and dir_map:
        per_date_path = ROOT / "reports" / "_tmp_per_date_direction_compare_v1.json"
        per_date_path.parent.mkdir(parents=True, exist_ok=True)
        per_date_path.write_text(
            json.dumps({"rows": dir_map}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        score_out = ROOT / "reports" / "_tmp_btrack_score_per_date_compare_v1.json"
        cmd_score = [
            sys.executable,
            str(ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"),
            "--hypothesis-json",
            str(ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"),
            "--btc-csv",
            str(args.btc_csv),
            "--per-date-direction-json",
            str(per_date_path),
            "--recent-trading-days",
            str(len(rows)),
            "--output",
            str(score_out),
        ]
        rc_s = subprocess.run(cmd_score, cwd=str(ROOT)).returncode
        eval_out = ROOT / "reports" / "_tmp_prophecy_hit_rate_per_date_compare_v1.json"
        cmd_eval = [
            sys.executable,
            str(ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"),
            "--run-mode",
            "price",
            "--score-json",
            str(score_out),
            "--output",
            str(eval_out),
        ]
        rc_e = subprocess.run(cmd_eval, cwd=str(ROOT)).returncode
        scored_eval = {
            "per_date_direction_json": str(per_date_path),
            "score_json": str(score_out),
            "eval_json": str(eval_out),
            "build_score_exit_code": rc_s,
            "eval_exit_code": rc_e,
            "eval_metrics": _load_json(eval_out),
        }

    def _pct(v: float | None) -> str:
        if v is None:
            return "n/a"
        return f"{100.0 * float(v):.2f}%"

    alert_lines = [
        "[MKM-DUAL-KPI]",
        "* [HYPO] observability only — KPI-A frozen headline unchanged; no Track A / live auto-promote.",
        (
            f"- KPI-A frozen (headline): {_pct(frozen_rate)} "
            f"(hits={frozen_m.get('price_hits')}/{frozen_m.get('n_evaluated')}) "
            f"mode={frozen_m.get('scoring_mode')}"
        ),
        (
            f"- KPI-B blocked WF OOS: {_pct(blocked_rate)} "
            f"(hits={blocked_m.get('directional_call_hits')}/{blocked_m.get('n_oos_dates')}) "
            f"delta_vs_frozen={_delta(frozen_rate, blocked_rate)}"
        ),
        (
            f"- KPI-B expanding OOS (min_train={expanding_m.get('min_train_rows')}): "
            f"{_pct(expanding_rate)} "
            f"(hits={expanding_m.get('directional_call_hits')}/{expanding_m.get('n_oos_dates')}) "
            f"delta_vs_frozen={_delta(frozen_rate, expanding_rate)}"
        ),
        "- Headline promotion still uses frozen until human picks KPI-B; see CENTRAL Dual-KPI v1.",
    ]
    if scored_eval and isinstance(scored_eval.get("eval_metrics"), dict):
        em = scored_eval["eval_metrics"]
        metrics = em.get("metrics") if isinstance(em.get("metrics"), dict) else {}
        alert_lines.append(
            f"- Per-date score chain (temp): {_pct(metrics.get('price_directional_hit_rate'))} "
            f"(n={metrics.get('n_evaluated')}, scoring_mode={metrics.get('scoring_mode')})"
        )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "inputs": {
            "score_json": str(args.score_json),
            "n_btc_rows": len(rows),
            "eval_date_first": str(rows[0].get("eval_date"))[:10],
            "eval_date_last": str(rows[-1].get("eval_date"))[:10],
            "train_objective": args.train_objective,
            "include_source_direction_signal": args.include_source_direction_signal,
            "include_expanded_prior_features": args.include_expanded_prior_features,
        },
        "comparison": {
            "frozen_single_direction_batch": frozen_m,
            "per_date_blocked_walkforward_oos": blocked_m,
            "per_date_expanding_walkforward_oos": expanding_m,
            "delta_blocked_minus_frozen": _delta(frozen_rate, blocked_rate),
            "delta_expanding_minus_frozen": _delta(frozen_rate, expanding_rate),
            "delta_expanding_minus_blocked": _delta(blocked_rate, expanding_rate),
        },
        "interpretation_ko": [
            "frozen: 오늘 가설 방향을 30일 전부에 복사한 채점(본선 headline과 동일).",
            "blocked_wf_oos: 승격 WF와 동일한 블록 OOS — 앞 10일은 test에 한 번도 안 나올 수 있음.",
            "expanding_oos: 각 날짜를 그 이전 날짜만으로 fit 후 예측(패널 전체 커버, 초기 min_train_rows 제외).",
            "Track A / btrack_prophecy_score_latest.json 은 변경하지 않음.",
        ],
        "scored_eval_chain": scored_eval,
        "alert_lines": alert_lines,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"frozen={frozen_rate} blocked_oos={blocked_rate} (n={blocked_m.get('n_oos_dates')}) "
        f"expanding={expanding_rate} (n={expanding_m.get('n_oos_dates')}) "
        f"delta_expanding-frozen={out['comparison']['delta_expanding_minus_frozen']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
