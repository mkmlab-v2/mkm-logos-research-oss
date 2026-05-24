#!/usr/bin/env python3
"""[HYPO] KPI-B shadow: per-date WF directions on same panel as KPI-A frozen headline.

Writes separate artifacts only (never overwrites prophecy_hit_rate_eval_latest.json or
btrack_prophecy_score_latest.json).

Outputs:
  docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json
  docs/final/artifacts/prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json
  reports/btrack_kpi_b_shadow_summary_v1_latest.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE_IN = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_SCORE_OUT = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
DEFAULT_EVAL_OUT = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"
DEFAULT_SUMMARY = ROOT / "reports/btrack_kpi_b_shadow_summary_v1_latest.json"
SCHEMA_SUMMARY = "btrack_kpi_b_shadow_summary_v1"


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


def _load_wf_module():
    path = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"
    spec = importlib.util.spec_from_file_location("prophecy_per_date_combo_wf", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _btc_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            r
            for r in (doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == "btc"
        ],
        key=lambda r: str(r.get("eval_date")),
    )


def _build_per_date_map(
    rows: list[dict[str, Any]],
    wf,
    km: dict,
    bm: dict,
    kf: dict,
    bf: dict,
    *,
    min_train_rows: int,
    include_source: bool,
    include_expanded: bool,
    train_objective: str,
    warmup_fallback: str,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """date -> predicted_direction; method tag per date."""
    direction_map: list[dict[str, str]] = []
    methods: dict[str, str] = {}
    for i, row in enumerate(rows):
        ed = str(row.get("eval_date"))[:10]
        pred: str | None = None
        method = "warmup_fallback"
        if i >= min_train_rows:
            train = rows[:i]
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
            if fitted is not None:
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
                method = "expanding_oos"
        if pred is None:
            pred = warmup_fallback
        direction_map.append({"eval_date": ed, "predicted_direction": pred})
        methods[ed] = method
    return direction_map, methods


def _rate_from_eval(doc: dict[str, Any] | None) -> tuple[float | None, int | None]:
    if not doc:
        return None, None
    m = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    rate = m.get("price_directional_hit_rate")
    n = m.get("n_evaluated")
    if isinstance(rate, (int, float)) and isinstance(n, int):
        return float(rate), n
    return None, None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_IN)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--hypothesis-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    ap.add_argument("--min-train-rows", type=int, default=3)
    ap.add_argument(
        "--warmup-fallback",
        choices=("frozen_hypothesis", "neutral"),
        default="frozen_hypothesis",
        help="Direction for first min_train_rows when expanding cannot run.",
    )
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="accuracy")
    ap.add_argument("--include-source-direction-signal", action="store_true", default=True)
    ap.add_argument("--no-include-source-direction-signal", action="store_false", dest="include_source_direction_signal")
    ap.add_argument("--include-expanded-prior-features", action="store_true", default=True)
    ap.add_argument("--no-include-expanded-prior-features", action="store_false", dest="include_expanded_prior_features")
    ap.add_argument("--score-out", type=Path, default=DEFAULT_SCORE_OUT)
    ap.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--kpi-a-eval-json", type=Path, default=ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json")
    ap.add_argument(
        "--promote-to-operational-headline",
        action="store_true",
        help="After success, copy shadow score/eval to operational headline pointers (requires approval workflow).",
    )
    args = ap.parse_args(argv)

    prod_score = _load_json(args.score_json)
    if not prod_score:
        raise SystemExit(f"missing prod score panel: {args.score_json}")
    rows = _btc_rows(prod_score)
    if not rows:
        raise SystemExit("no btc rows in prod score")

    hypo = _load_json(args.hypothesis_json) or {}
    frozen_dir = str((hypo.get("prediction") or {}).get("direction") or "bear").strip().lower()
    warmup = frozen_dir if args.warmup_fallback == "frozen_hypothesis" else "neutral"

    wf = _load_wf_module()
    km = wf._prior_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bm = wf._prior_map(args.btc_csv) if args.btc_csv.is_file() else {}
    kf = wf._feature_map(args.kospi_csv) if args.kospi_csv.is_file() else {}
    bf = wf._feature_map(args.btc_csv) if args.btc_csv.is_file() else {}

    dir_map, methods = _build_per_date_map(
        rows,
        wf,
        km,
        bm,
        kf,
        bf,
        min_train_rows=args.min_train_rows,
        include_source=args.include_source_direction_signal,
        include_expanded=args.include_expanded_prior_features,
        train_objective=args.train_objective,
        warmup_fallback=warmup,
    )

    per_date_path = ROOT / "reports" / "_tmp_kpi_b_per_date_directions_v1.json"
    per_date_path.parent.mkdir(parents=True, exist_ok=True)
    per_date_path.write_text(
        json.dumps({"rows": dir_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    recent_days = len(rows)
    cmd_score = [
        sys.executable,
        str(ROOT / "scripts" / "build_btrack_prophecy_score_from_ohlcv.py"),
        "--hypothesis-json",
        str(args.hypothesis_json),
        "--btc-csv",
        str(args.btc_csv),
        "--per-date-direction-json",
        str(per_date_path),
        "--recent-trading-days",
        str(recent_days),
        "--output",
        str(args.score_out),
    ]
    rc_s = subprocess.run(cmd_score, cwd=str(ROOT)).returncode
    if rc_s != 0:
        raise SystemExit(rc_s)

    cmd_eval = [
        sys.executable,
        str(ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"),
        "--run-mode",
        "price",
        "--score-json",
        str(args.score_out),
        "--output",
        str(args.eval_out),
    ]
    rc_e = subprocess.run(cmd_eval, cwd=str(ROOT)).returncode
    if rc_e != 0:
        raise SystemExit(rc_e)

    kpi_a = _load_json(args.kpi_a_eval_json)
    kpi_b = _load_json(args.eval_out)
    rate_a, n_a = _rate_from_eval(kpi_a)
    rate_b, n_b = _rate_from_eval(kpi_b)
    delta = round(rate_b - rate_a, 6) if rate_a is not None and rate_b is not None else None

    n_expanding = sum(1 for m in methods.values() if m == "expanding_oos")
    n_warmup = sum(1 for m in methods.values() if m == "warmup_fallback")

    operator_lines = [
        "[MKM-KPI-B-SHADOW]",
        "* [HYPO] shadow headline only — KPI-A prod eval unchanged.",
        (
            f"- KPI-A frozen: {rate_a:.2%} (n={n_a}) "
            f"scoring_mode=frozen_single_direction_batch"
            if rate_a is not None
            else "- KPI-A frozen: n/a"
        ),
        (
            f"- KPI-B per-date WF: {rate_b:.2%} (n={n_b}) "
            f"scoring_mode=per_date_direction_overrides "
            f"delta_vs_A={delta}"
            if rate_b is not None
            else "- KPI-B per-date WF: n/a"
        ),
        f"- Per-date methods: expanding_oos={n_expanding} warmup_fallback={n_warmup} (min_train={args.min_train_rows})",
    ]

    summary: dict[str, Any] = {
        "schema": SCHEMA_SUMMARY,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "inputs": {
            "prod_score_json": str(args.score_json),
            "min_train_rows": args.min_train_rows,
            "warmup_fallback": args.warmup_fallback,
        },
        "artifacts": {
            "kpi_a_eval_json": str(args.kpi_a_eval_json),
            "kpi_b_score_json": str(args.score_out),
            "kpi_b_eval_json": str(args.eval_out),
        },
        "kpi_a": {"price_directional_hit_rate": rate_a, "n_evaluated": n_a},
        "kpi_b": {"price_directional_hit_rate": rate_b, "n_evaluated": n_b},
        "delta_b_minus_a": delta,
        "operator_lines": operator_lines,
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for line in operator_lines:
        print(line)
    print(f"WROTE: {args.score_out.resolve()}")
    print(f"WROTE: {args.eval_out.resolve()}")
    print(f"WROTE: {args.summary_out.resolve()}")

    if args.promote_to_operational_headline:
        approval_path = ROOT / "docs/final/artifacts/btrack_dual_kpi_headline_human_approval_v1_latest.json"
        approval = _load_json(approval_path) or {}
        if str(approval.get("decision") or "") != "APPROVED_KPI_B_OPERATIONAL_HEADLINE":
            print(
                f"SKIP promote: no approval at {approval_path} "
                "(run apply_btrack_dual_kpi_headline_human_approval_v1.py first)",
                file=sys.stderr,
            )
        else:
            oper_eval = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
            oper_score = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
            shutil.copy2(args.eval_out, oper_eval)
            shutil.copy2(args.score_out, oper_score)
            print(f"PROMOTED shadow -> {oper_eval.resolve()} + {oper_score.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
