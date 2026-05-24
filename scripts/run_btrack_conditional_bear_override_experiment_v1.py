#!/usr/bin/env python3
"""[HYPO] Conditional bear override sweep (30d BTC; wrong_dir cohort metrics)."""
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
DEFAULT_OUT = ROOT / "reports/btrack_conditional_bear_override_experiment_v1_latest.json"
WORK = ROOT / "reports/btrack_cbo_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"

_CBO_STD = {
    "enabled": True,
    "when": {
        "price_score_min": 0.03,
        "last_return_negative": True,
        "weighted_min": 0.03,
    },
    "action": "negate_weighted",
}

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline"},
    {"slug": "cbo_std", "conditional_bear_override": _CBO_STD},
    {
        "slug": "cbo_macro",
        "conditional_bear_override": {
            **_CBO_STD,
            "when": {**_CBO_STD["when"], "require_macro_bull": True, "macro_score_min": 0.0},
        },
    },
    {
        "slug": "cbo_force_bear",
        "conditional_bear_override": {**_CBO_STD, "action": "force_bear"},
    },
    {
        "slug": "cbo_halve",
        "conditional_bear_override": {**_CBO_STD, "action": "halve_and_negate"},
    },
    {
        "slug": "cbo_loose_price",
        "conditional_bear_override": {
            **_CBO_STD,
            "when": {**_CBO_STD["when"], "price_score_min": 0.01},
        },
    },
    {
        "slug": "cbo_tight_w",
        "conditional_bear_override": {
            **_CBO_STD,
            "when": {**_CBO_STD["when"], "weighted_min": 0.05},
        },
    },
    {
        "slug": "cbo_plus_flip_last",
        "conditional_bear_override": _CBO_STD,
        "price_lens_calibration": {"flip_to_bear_when_last_negative": True},
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
    cbo = spec.get("conditional_bear_override")
    if isinstance(cbo, dict):
        rules["conditional_bear_override"] = cbo
    else:
        rules.pop("conditional_bear_override", None)
    cal = spec.get("price_lens_calibration")
    if isinstance(cal, dict):
        rules["price_lens_calibration"] = cal
    cfg["rules"] = rules
    return cfg


def _rows_metrics(per_date_path: Path, wrong_dates: list[str]) -> dict[str, Any]:
    doc = _load(per_date_path)
    preds: dict[str, str] = {}
    cbo_days: list[str] = []
    bear_fix = 0
    for r in doc.get("rows") or []:
        if not isinstance(r, dict) or str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date"))[:10]
        pred = str(r.get("predicted_direction") or "neutral").lower()
        preds[ed] = pred
        if r.get("conditional_bear_override_applied"):
            cbo_days.append(ed)
    for ed in wrong_dates:
        if preds.get(ed) == "bear":
            bear_fix += 1
    return {
        "n_wrong_dates": len(wrong_dates),
        "n_bear_fix": bear_fix,
        "n_cbo_applied": len(cbo_days),
        "cbo_applied_dates": sorted(cbo_days),
    }


def _run_variant(*, slug: str, cfg: dict[str, Any], work_dir: Path, wrong_dates: list[str]) -> dict[str, Any]:
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
    ev = _load(eval_out)
    return {
        "slug": slug,
        "rules": cfg.get("rules"),
        "metrics": _metrics_btc(ev),
        "alert_1_pass": float((ev.get("metrics") or {}).get("price_directional_hit_rate") or 0) >= 0.5,
        "per_date_path": str(per_date.resolve()),
        "wrong_dir_cohort": _rows_metrics(per_date, wrong_dates),
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

    wrong_dates = list(_load(args.counterfactual_json).get("wrong_direction_dates") or []) if args.counterfactual_json.is_file() else []
    if not wrong_dates:
        print("No wrong_direction dates.", file=sys.stderr)
        return 2

    base_cfg = _load(args.ensemble_config)
    baseline_m = _metrics_btc(_load(args.baseline_eval)) if args.baseline_eval.is_file() else {}
    rows: list[dict[str, Any]] = []
    for spec in VARIANTS:
        slug = str(spec["slug"])
        print(f"==> cbo {slug}", file=sys.stderr)
        try:
            rows.append(_run_variant(slug=slug, cfg=_apply_variant(base_cfg, spec), work_dir=WORK, wrong_dates=wrong_dates))
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:500]})

    ok = [r for r in rows if "metrics" in r]
    best_a1 = max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    best_fix = max(ok, key=lambda r: int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0)) if ok else None
    best_pareto = _pareto_pick(ok)

    report = {
        "schema": "btrack_conditional_bear_override_experiment_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "wrong_direction_dates": wrong_dates,
        "baseline_metrics": baseline_m,
        "variants": rows,
        "best_by_headline_all_rows": best_a1,
        "best_by_wrong_dir_bear_fix": best_fix,
        "pareto_recommendation": best_pareto,
        "operator_lines": _operator_lines(baseline_m, best_a1, best_fix, best_pareto),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        print(line)
    return 0


def _pareto_pick(ok: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer variants that fix wrong_dir days without collapsing headline vs baseline."""
    if not ok:
        return None
    baseline_row = next((r for r in ok if r.get("slug") == "baseline"), ok[0])
    base_rate = float((baseline_row.get("metrics") or {}).get("price_directional_hit_rate") or 0)
    with_fix = [r for r in ok if int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0) > 0]
    if with_fix:
        return max(
            with_fix,
            key=lambda r: (
                float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0),
                int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0),
            ),
        )
    return max(
        ok,
        key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0),
    )


def _operator_lines(
    baseline: dict[str, Any],
    best_a1: dict[str, Any] | None,
    best_fix: dict[str, Any] | None,
    pareto: dict[str, Any] | None,
) -> list[str]:
    lines = [
        f"- [MKM-CBO] baseline all-rows {float(baseline.get('price_directional_hit_rate') or 0):.1%}"
    ]
    if pareto:
        m = pareto.get("metrics") or {}
        wc = pareto.get("wrong_dir_cohort") or {}
        lines.append(
            f"- [MKM-CBO] pareto {pareto.get('slug')}: all-rows {float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"bear_fix={wc.get('n_bear_fix')}/7 cbo_fires={wc.get('n_cbo_applied')} "
            f"A1={'pass' if pareto.get('alert_1_pass') else 'fail'}"
        )
    if best_fix and best_fix.get("slug") != (pareto or {}).get("slug"):
        wc = best_fix.get("wrong_dir_cohort") or {}
        m = best_fix.get("metrics") or {}
        lines.append(
            f"- [MKM-CBO] best bear_fix {best_fix.get('slug')}: {wc.get('n_bear_fix')}/7 "
            f"all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
