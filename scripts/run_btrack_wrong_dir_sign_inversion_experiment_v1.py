#!/usr/bin/env python3
"""[HYPO] Wrong-dir cohort: price-lens sign inversion / bear-flip experiments (30d, reports/ only)."""
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DEFAULT_BASELINE_EVAL = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_wrong_dir_sign_inversion_experiment_v1_latest.json"
WORK = ROOT / "reports/btrack_wrong_dir_sign_inv_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline", "price_lens_calibration": {}},
    {
        "slug": "invert_sign",
        "price_lens_calibration": {"invert_price_score_sign": True},
    },
    {
        "slug": "flip_last_neg",
        "price_lens_calibration": {"flip_to_bear_when_last_negative": True},
    },
    {
        "slug": "flip_avg_neg",
        "price_lens_calibration": {"flip_to_bear_when_avg_negative": True},
    },
    {
        "slug": "flip_last_and_avg",
        "price_lens_calibration": {
            "flip_to_bear_when_last_negative": True,
            "flip_to_bear_when_avg_negative": True,
        },
    },
    {
        "slug": "flip_last_blend035",
        "price_lens_calibration": {
            "flip_to_bear_when_last_negative": True,
            "last_day_blend": 0.35,
        },
    },
    {
        "slug": "invert_flip_last",
        "price_lens_calibration": {
            "invert_price_score_sign": True,
            "flip_to_bear_when_last_negative": True,
        },
    },
    {
        "slug": "flip_avg_scale025",
        "price_lens_calibration": {
            "flip_to_bear_when_avg_negative": True,
            "return_scale_divisor": 0.025,
        },
    },
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_btc(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "price_hits": m.get("price_hits"),
        "n_evaluated": m.get("n_evaluated"),
    }


def _apply_variant(base_cfg: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base_cfg)
    rules = dict(cfg.get("rules") or {})
    cal = dict(spec.get("price_lens_calibration") or {})
    if cal:
        rules["price_lens_calibration"] = cal
    elif spec.get("slug") == "baseline":
        rules.pop("price_lens_calibration", None)
    cfg["rules"] = rules
    return cfg


def _btc_preds(per_date_path: Path) -> dict[str, str]:
    doc = _load(per_date_path)
    return {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "neutral").lower()
        for r in (doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }


def _wrong_dir_cohort_metrics(
    per_date_path: Path,
    wrong_dates: list[str],
    *,
    baseline_preds: dict[str, str],
) -> dict[str, Any]:
    preds = _btc_preds(per_date_path)
    bear_fix = 0
    bear_calls = 0
    still_bull = 0
    flipped_off_bull = 0
    for ed in wrong_dates:
        pred = preds.get(ed, "neutral")
        base = baseline_preds.get(ed, "neutral")
        if pred == "bear":
            bear_calls += 1
            bear_fix += 1
        elif pred == "bull":
            still_bull += 1
        if base == "bull" and pred in ("bear", "neutral"):
            flipped_off_bull += 1
    return {
        "n_wrong_dates": len(wrong_dates),
        "n_bear_fix": bear_fix,
        "n_bear_calls_on_cohort": bear_calls,
        "n_still_bull": still_bull,
        "n_flipped_off_bull": flipped_off_bull,
    }


def _run_variant(*, slug: str, cfg: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = work_dir / f"ensemble_{slug}.json"
    per_date = work_dir / f"per_date_{slug}.json"
    score = work_dir / f"score_{slug}.json"
    eval_out = work_dir / f"eval_{slug}.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for cmd in [
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
            "--ensemble-config",
            str(cfg_path.relative_to(ROOT)),
            "--output",
            str(per_date.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            "30",
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC_CSV.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI_CSV.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ],
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(eval_out.relative_to(ROOT)),
        ],
    ]:
        proc = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"{' '.join(cmd)}\n{proc.stderr or proc.stdout}")
    return {
        "slug": slug,
        "rules": cfg.get("rules"),
        "metrics": _metrics_btc(_load(eval_out)),
        "alert_1_pass": float((_load(eval_out).get("metrics") or {}).get("price_directional_hit_rate") or 0) >= 0.5,
        "per_date_path": str(per_date.resolve()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--counterfactual-json", type=Path, default=DEFAULT_CF)
    ap.add_argument("--baseline-eval", type=Path, default=DEFAULT_BASELINE_EVAL)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not BUNDLE.is_file() or not BTC_CSV.is_file():
        print("Missing bundle or BTC CSV.", file=sys.stderr)
        return 2

    wrong_dates: list[str] = []
    if args.counterfactual_json.is_file():
        wrong_dates = list(_load(args.counterfactual_json).get("wrong_direction_dates") or [])
    if not wrong_dates:
        print("No wrong_direction dates in counterfactual JSON.", file=sys.stderr)
        return 2

    base_cfg = _load(args.ensemble_config)
    baseline_m = _metrics_btc(_load(args.baseline_eval)) if args.baseline_eval.is_file() else {}
    rows: list[dict[str, Any]] = []
    baseline_preds: dict[str, str] = {}

    for spec in VARIANTS:
        slug = str(spec["slug"])
        cfg = _apply_variant(base_cfg, spec)
        print(f"==> sign_inv {slug}", file=sys.stderr)
        try:
            row = _run_variant(slug=slug, cfg=cfg, work_dir=WORK)
            if slug == "baseline":
                baseline_preds = _btc_preds(Path(row["per_date_path"]))
            elif not baseline_preds:
                base_path = WORK / "per_date_baseline.json"
                if base_path.is_file():
                    baseline_preds = _btc_preds(base_path)
            row["wrong_dir_cohort"] = _wrong_dir_cohort_metrics(
                Path(row["per_date_path"]), wrong_dates, baseline_preds=baseline_preds
            )
            rows.append(row)
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:500]})

    ok = [r for r in rows if "metrics" in r]
    best_a1 = max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    best_fix = max(ok, key=lambda r: int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0)) if ok else None

    sweep_for_cf = {
        "wrong_dir_dates": wrong_dates,
        "variants": [
            {**r, "per_date_path": r.get("per_date_path")}
            for r in ok
            if r.get("per_date_path")
        ],
    }
    cf_path = ROOT / "reports/btrack_wrong_dir_sign_inv_counterfactual_v1_latest.json"
    cf_path.write_text(json.dumps(sweep_for_cf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cf_script = ROOT / "scripts/build_btrack_wrong_dir_counterfactual_matrix_v1.py"
    if cf_script.is_file() and ok:
        subprocess.run(
            [
                sys.executable,
                str(cf_script.relative_to(ROOT)),
                "--sweep-json",
                str(cf_path.relative_to(ROOT)),
                "--output",
                "reports/btrack_wrong_dir_sign_inv_counterfactual_matrix_v1_latest.json",
            ],
            cwd=ROOT,
        )

    report = {
        "schema": "btrack_wrong_dir_sign_inversion_experiment_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "wrong_direction_dates": wrong_dates,
        "baseline_metrics": baseline_m,
        "variants": rows,
        "best_by_headline_all_rows": best_a1,
        "best_by_wrong_dir_bear_fix": best_fix,
        "alert_1_floor": 0.5,
        "promotion_note": "Sign inversion is research_only; production ensemble unchanged.",
        "operator_lines": _operator_lines(baseline_m, best_a1, best_fix, wrong_dates),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        print(line)
    return 0


def _operator_lines(
    baseline: dict[str, Any],
    best_a1: dict[str, Any] | None,
    best_fix: dict[str, Any] | None,
    wrong_dates: list[str],
) -> list[str]:
    n = len(wrong_dates)
    lines = [
        (
            f"- [MKM-SIGN-INV] prod baseline all-rows "
            f"{float(baseline.get('price_directional_hit_rate') or 0):.1%}; cohort n={n}"
        )
    ]
    if best_fix and best_fix.get("wrong_dir_cohort"):
        wc = best_fix["wrong_dir_cohort"]
        m = best_fix.get("metrics") or {}
        lines.append(
            f"- [MKM-SIGN-INV] best bear_fix {best_fix.get('slug')}: "
            f"{wc.get('n_bear_fix')}/{n} bear_calls={wc.get('n_bear_calls_on_cohort')} "
            f"all-rows {float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"A1={'pass' if best_fix.get('alert_1_pass') else 'fail'}"
        )
    if best_a1 and best_a1.get("slug") != (best_fix or {}).get("slug"):
        m = best_a1.get("metrics") or {}
        wc = best_a1.get("wrong_dir_cohort") or {}
        lines.append(
            f"- [MKM-SIGN-INV] best A1 {best_a1.get('slug')}: all-rows "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"bear_fix={wc.get('n_bear_fix')}/{n}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
