#!/usr/bin/env python3
"""[HYPO] Sweep price-lens bear-day calibration knobs (30d BTC headline, reports/ only)."""
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
DEFAULT_BASELINE_EVAL = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_WRONG = ROOT / "reports/btrack_wrong_direction_lens_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_price_lens_bear_calibration_sweep_v1_latest.json"
WORK = ROOT / "reports/btrack_price_lens_cal_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"

# Focused grid (wrong_dir cohort motivated; not full factorial).
VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline", "price_lens_calibration": {}},
    {"slug": "blend035", "price_lens_calibration": {"last_day_blend": 0.35}},
    {"slug": "blend050", "price_lens_calibration": {"last_day_blend": 0.5}},
    {"slug": "damp060", "price_lens_calibration": {"bear_dampen_if_last_day_negative": 0.6}},
    {"slug": "damp075", "price_lens_calibration": {"bear_dampen_if_last_day_negative": 0.75}},
    {"slug": "scale025", "price_lens_calibration": {"return_scale_divisor": 0.025}},
    {"slug": "lb3", "price_lookback_days": 3},
    {"slug": "lb7", "price_lookback_days": 7},
    {"slug": "lb3_blend040", "price_lookback_days": 3, "price_lens_calibration": {"last_day_blend": 0.4}},
    {"slug": "blend040_damp070", "price_lens_calibration": {"last_day_blend": 0.4, "bear_dampen_if_last_day_negative": 0.7}},
    {"slug": "blend050_damp060", "price_lens_calibration": {"last_day_blend": 0.5, "bear_dampen_if_last_day_negative": 0.6}},
    {"slug": "lb3_damp060", "price_lookback_days": 3, "price_lens_calibration": {"bear_dampen_if_last_day_negative": 0.6}},
    {"slug": "scale025_blend035", "price_lens_calibration": {"return_scale_divisor": 0.025, "last_day_blend": 0.35}},
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
    if "price_lookback_days" in spec:
        rules["price_lookback_days"] = int(spec["price_lookback_days"])
    cal = dict(spec.get("price_lens_calibration") or {})
    if cal:
        rules["price_lens_calibration"] = cal
    elif "price_lens_calibration" in rules and spec.get("slug") == "baseline":
        rules.pop("price_lens_calibration", None)
    cfg["rules"] = rules
    return cfg


def _run_variant(*, slug: str, cfg: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = work_dir / f"ensemble_{slug}.json"
    per_date = work_dir / f"per_date_{slug}.json"
    score = work_dir / f"score_{slug}.json"
    eval_out = work_dir / f"eval_{slug}.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps = [
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
    ]
    for cmd in steps:
        proc = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"{' '.join(cmd)}\n{proc.stderr or proc.stdout}")
    ev = _load(eval_out)
    per_doc = _load(per_date)
    return {
        "slug": slug,
        "rules": cfg.get("rules"),
        "metrics": _metrics_btc(ev),
        "alert_1_pass": float((ev.get("metrics") or {}).get("price_directional_hit_rate") or 0) >= 0.5,
        "per_date_path": str(per_date),
        "n_per_date_rows": len(per_doc.get("rows") or []),
    }


def _wrong_dir_flip_count(per_date_path: Path, wrong_dates: set[str]) -> dict[str, Any]:
    if not per_date_path.is_file() or not wrong_dates:
        return {"n_wrong_dates": 0, "n_flipped_to_bear_or_neutral": 0}
    doc = _load(per_date_path)
    flipped = 0
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed not in wrong_dates:
            continue
        pred = str(r.get("predicted_direction") or "").lower()
        if pred in ("bear", "neutral"):
            flipped += 1
    return {
        "n_wrong_dates": len(wrong_dates),
        "n_flipped_to_bear_or_neutral": flipped,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-eval", type=Path, default=DEFAULT_BASELINE_EVAL)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--wrong-dir-report", type=Path, default=DEFAULT_WRONG)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not BUNDLE.is_file() or not BTC_CSV.is_file():
        print("Missing bundle or BTC CSV.", file=sys.stderr)
        return 2

    wrong_dates: set[str] = set()
    if args.wrong_dir_report.is_file():
        wd = _load(args.wrong_dir_report)
        for d in wd.get("wrong_direction_days") or []:
            if isinstance(d, dict) and d.get("eval_date"):
                wrong_dates.add(str(d["eval_date"])[:10])

    base_cfg = _load(args.ensemble_config)
    baseline_m = _metrics_btc(_load(args.baseline_eval)) if args.baseline_eval.is_file() else {}
    rows: list[dict[str, Any]] = []
    for spec in VARIANTS:
        slug = str(spec["slug"])
        cfg = _apply_variant(base_cfg, spec)
        print(f"==> price_lens_cal {slug}", file=sys.stderr)
        try:
            row = _run_variant(slug=slug, cfg=cfg, work_dir=WORK)
            row["wrong_dir_cohort"] = _wrong_dir_flip_count(Path(row["per_date_path"]), wrong_dates)
            rows.append(row)
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:500]})

    ok = [r for r in rows if "metrics" in r]
    best_a1 = (
        max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    )
    best_flip = (
        max(
            ok,
            key=lambda r: int((r.get("wrong_dir_cohort") or {}).get("n_flipped_to_bear_or_neutral") or 0),
        )
        if ok
        else None
    )
    report = {
        "schema": "btrack_price_lens_bear_calibration_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "wrong_dir_dates": sorted(wrong_dates),
        "baseline_metrics": baseline_m,
        "variants": rows,
        "best_by_headline_all_rows": best_a1,
        "best_by_wrong_dir_flip": best_flip,
        "alert_1_floor": 0.5,
        "promotion_note": (
            "Do not write docs/final/artifacts/btrack_lens_ensemble_v1.json without ALERT_1 pass "
            "and holdout review; production min_conf=0.18 unchanged by this sweep."
        ),
        "operator_lines": _operator_lines(baseline_m, best_a1, best_flip, wrong_dates),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        print(line)

    cf_script = ROOT / "scripts/build_btrack_wrong_dir_counterfactual_matrix_v1.py"
    if cf_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(cf_script.relative_to(ROOT)), "--sweep-json", str(args.output.relative_to(ROOT))],
            cwd=ROOT,
        )
        if proc.returncode != 0:
            print("counterfactual matrix step failed (non-fatal for sweep)", file=sys.stderr)
    return 0


def _operator_lines(
    baseline: dict[str, Any],
    best_a1: dict[str, Any] | None,
    best_flip: dict[str, Any] | None,
    wrong_dates: set[str],
) -> list[str]:
    lines = [
        (
            f"- [MKM-PRICE-LENS-CAL] baseline prod@0.18: all-rows "
            f"{float(baseline.get('price_directional_hit_rate') or 0):.1%} "
            f"(wrong_dir cohort n={len(wrong_dates)})"
        )
    ]
    if best_a1 and best_a1.get("metrics"):
        m = best_a1["metrics"]
        wc = best_a1.get("wrong_dir_cohort") or {}
        lines.append(
            f"- [MKM-PRICE-LENS-CAL] best A1 {best_a1.get('slug')}: all-rows "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"flip_wrong={wc.get('n_flipped_to_bear_or_neutral')}/{wc.get('n_wrong_dates')} "
            f"A1={'pass' if best_a1.get('alert_1_pass') else 'fail'}"
        )
    if best_flip and best_flip.get("slug") != (best_a1 or {}).get("slug"):
        wc = best_flip.get("wrong_dir_cohort") or {}
        m = best_flip.get("metrics") or {}
        lines.append(
            f"- [MKM-PRICE-LENS-CAL] best wrong-dir flip {best_flip.get('slug')}: "
            f"flip={wc.get('n_flipped_to_bear_or_neutral')}/{wc.get('n_wrong_dates')} "
            f"all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
