#!/usr/bin/env python3
"""[HYPO] v1 per-date margin/penalty/min_conf variants on frozen KPI-A anchor dates (BTC).

Tests whether stronger abstain (tie_break_min_margin, neutral_penalty) lifts 30d all-rows hit rate.
Does not modify production *_latest.json. B-track only; no Track A / live auto-promote.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
BASELINE_EVAL = ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_margin_penalty_grid_v1_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_margin_penalty_grid_work"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline_cfg"},
    {"slug": "margin_020", "tie_break_min_margin": 0.02},
    {"slug": "margin_025", "tie_break_min_margin": 0.025},
    {"slug": "margin_035", "tie_break_min_margin": 0.035},
    {"slug": "margin_040", "tie_break_min_margin": 0.04},
    {"slug": "margin_050", "tie_break_min_margin": 0.05},
    {"slug": "neutral_pen_m05", "neutral_penalty": -0.05},
    {"slug": "neutral_pen_m15", "neutral_penalty": -0.15},
    {"slug": "min_conf_016", "min_direction_confidence": 0.16},
    {"slug": "min_conf_017", "min_direction_confidence": 0.17},
    {"slug": "margin020_min017", "tie_break_min_margin": 0.02, "min_direction_confidence": 0.17},
    {"slug": "margin025_penm05", "tie_break_min_margin": 0.025, "neutral_penalty": -0.05},
    {"slug": "margin040_min016", "tie_break_min_margin": 0.04, "min_direction_confidence": 0.16},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_cfg(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    for key in ("tie_break_min_margin", "neutral_penalty", "min_direction_confidence"):
        if key in spec:
            rules[key] = spec[key]
    cfg["rules"] = rules
    return cfg


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{proc.stderr or proc.stdout}")


def _anchor_dates(score_path: Path) -> list[str]:
    doc = _load(score_path)
    return sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in (doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
    )


def _score_dir_stats(score_path: Path) -> dict[str, Any]:
    rows = [
        r
        for r in (_load(score_path).get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    ]
    all_h = all_n = dir_h = dir_n = neu = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        hit = pred in ("bull", "bear") and act in ("bull", "bear") and pred == act
        all_n += 1
        if hit:
            all_h += 1
        if pred in ("bull", "bear"):
            dir_n += 1
            if hit:
                dir_h += 1
        elif pred == "neutral":
            neu += 1
    return {
        "all_rows_hit_rate": round(all_h / all_n, 6) if all_n else None,
        "dir_only_hit_rate": round(dir_h / dir_n, 6) if dir_n else None,
        "n_evaluated": all_n,
        "n_directional_calls": dir_n,
        "n_neutral_predictions": neu,
        "price_hits": all_h,
    }


def _metrics(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "n_evaluated": m.get("n_evaluated"),
        "price_hits": m.get("price_hits"),
    }


def _run_variant(
    spec: dict[str, Any],
    *,
    base_cfg: dict[str, Any],
    dates_path: Path,
    anchor_score: Path,
    work_dir: Path,
) -> dict[str, Any]:
    slug = str(spec["slug"])
    cfg = _apply_cfg(base_cfg, spec)
    cfg_path = work_dir / f"ens_{slug}.json"
    per_date = work_dir / f"per_date_{slug}.json"
    score_out = work_dir / f"score_{slug}.json"
    eval_out = work_dir / f"eval_{slug}.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    py = sys.executable
    _run(
        [
            py,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--score-json",
            str(anchor_score.relative_to(ROOT)),
            "--ensemble-config",
            str(cfg_path.relative_to(ROOT)),
            "--ensemble-mode",
            "v1",
            "--output",
            str(per_date.relative_to(ROOT)),
        ]
    )
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            str(BTC_CSV.relative_to(ROOT)),
            "--batch-eval-dates-json",
            str(dates_path.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score_out.relative_to(ROOT)),
        ]
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_out.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_out.relative_to(ROOT)),
        ]
    )
    per_doc = _load(per_date)
    neu = sum(
        1
        for r in (per_doc.get("rows") or [])
        if isinstance(r, dict)
        and str(r.get("predicted_direction") or "").lower() in ("neutral", "abstain")
    )
    ev_m = _metrics(_load(eval_out))
    sc = _score_dir_stats(score_out)
    hr = float(ev_m.get("price_directional_hit_rate") or sc.get("all_rows_hit_rate") or 0)
    return {
        "slug": slug,
        "rules_applied": {
            k: cfg["rules"].get(k)
            for k in ("tie_break_min_margin", "neutral_penalty", "min_direction_confidence")
        },
        "metrics": ev_m,
        "score_derived": sc,
        "alert_1_pass_50pct_all_rows": hr >= 0.5,
        "n_per_date_neutral": neu,
        "paths": {
            "ensemble_config": str(cfg_path),
            "per_date_json": str(per_date),
            "score_json": str(score_out),
            "eval_json": str(eval_out),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor-score", type=Path, default=ANCHOR_SCORE)
    ap.add_argument("--baseline-eval", type=Path, default=BASELINE_EVAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--work-dir", type=Path, default=WORK)
    ap.add_argument("--run-promotion-gates-on-best", action="store_true")
    args = ap.parse_args()

    if not args.anchor_score.is_file() or not args.baseline_eval.is_file():
        print("Missing anchor score or baseline eval.", file=sys.stderr)
        return 2
    if not DEFAULT_CFG.is_file() or not BTC_CSV.is_file():
        print("Missing ensemble config or BTC CSV.", file=sys.stderr)
        return 2

    dates = _anchor_dates(args.anchor_score)
    if not dates:
        print("No BTC dates in anchor.", file=sys.stderr)
        return 2

    args.work_dir.mkdir(parents=True, exist_ok=True)
    dates_path = args.work_dir / "anchor_eval_dates.json"
    dates_path.write_text(json.dumps({"eval_dates": dates}, indent=2) + "\n", encoding="utf-8")

    base_cfg = _load(DEFAULT_CFG)
    base_m = _metrics(_load(args.baseline_eval))
    rows: list[dict[str, Any]] = []
    for spec in VARIANTS:
        print(f"==> frozen30d margin_penalty {spec['slug']}", file=sys.stderr)
        try:
            row = _run_variant(
                spec,
                base_cfg=base_cfg,
                dates_path=dates_path,
                anchor_score=args.anchor_score,
                work_dir=args.work_dir,
            )
            bm = base_m
            cm = row["metrics"]
            row["delta_vs_frozen_kpi_a"] = {
                "price_directional_hit_rate": round(
                    float(cm.get("price_directional_hit_rate") or row["score_derived"].get("all_rows_hit_rate") or 0)
                    - float(bm.get("price_directional_hit_rate") or 0),
                    6,
                ),
            }
            rows.append(row)
        except RuntimeError as e:
            rows.append({"slug": spec["slug"], "error": str(e)[:500]})

    ok = [r for r in rows if "metrics" in r]

    def _hr(r: dict[str, Any]) -> float:
        return float(
            (r.get("metrics") or {}).get("price_directional_hit_rate")
            or (r.get("score_derived") or {}).get("all_rows_hit_rate")
            or 0
        )

    best = max(ok, key=_hr) if ok else None
    gates_block: dict[str, Any] | None = None
    if best and args.run_promotion_gates_on_best and best.get("alert_1_pass_50pct_all_rows"):
        per_best = Path(best["paths"]["per_date_json"])
        gates_out = args.work_dir / f"promotion_gates_best_{best['slug']}.json"
        summary_out = args.work_dir / f"recommended_chain_summary_best_{best['slug']}.json"
        cmd = [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            "180",
            "--per-date-direction-json",
            str(per_best.relative_to(ROOT)),
            "--gates-out",
            str(gates_out.relative_to(ROOT)),
            "--summary-out",
            str(summary_out.relative_to(ROOT)),
            "--calibration-note",
            f"frozen30d_margin_penalty_best={best['slug']}",
        ]
        rc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        gates_block = {"exit_code": rc.returncode, "gates_json": str(gates_out)}
        if gates_out.is_file():
            g = _load(gates_out)
            gates_block["combined_all_passed"] = bool(g.get("combined_all_passed"))
            gates_block["outcome_class"] = g.get("outcome_class")

    report = {
        "schema": "btrack_frozen30d_margin_penalty_grid_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": "frozen_kpi_a_30d_anchor_dates_btc",
        "frozen_kpi_a_baseline_metrics": base_m,
        "variants": rows,
        "best_by_all_rows_hit_rate": best["slug"] if best else None,
        "best_metrics": best.get("metrics") if best else None,
        "best_score_derived": best.get("score_derived") if best else None,
        "best_alert_1_pass_50pct": best.get("alert_1_pass_50pct_all_rows") if best else False,
        "promotion_gates_on_best": gates_block,
        "combo_reference_ms_hybrid_60pct": {
            "rule_id": "agree_or_ms_else_v1",
            "all_rows_hit_rate": 0.6,
            "source": "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json",
        },
        "track_a_auto_promote": False,
        "note": "Ensemble rules override per variant; batch-eval-dates frozen anchor. MS hybrid 60% remains B-track combo leader unless a variant exceeds it on same panel.",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        sc = best.get("score_derived") or {}
        print(
            f"BEST slug={best['slug']} all-rows={_hr(best):.1%} "
            f"dir-only={sc.get('dir_only_hit_rate')} neutral={sc.get('n_neutral_predictions')} "
            f"A1={'pass' if best.get('alert_1_pass_50pct_all_rows') else 'fail'}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
