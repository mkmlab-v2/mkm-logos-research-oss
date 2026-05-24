#!/usr/bin/env python3
"""[HYPO] RFC F2 prior-range + F3 vol-regime experiment (30d BTC headline)."""
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
DEFAULT_OUT = ROOT / "reports/btrack_rfc_f2_f3_experiment_v1_latest.json"
WORK = ROOT / "reports/btrack_rfc_f2_f3_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

_CBO_OVN = {
    "enabled": True,
    "when": {
        "price_score_min": 0.03,
        "overnight_negative": True,
        "weighted_min": 0.03,
    },
    "action": "negate_weighted",
}

_VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline"},
    {"slug": "f2_blend030", "price_lens_calibration": {"prior_range_blend": 0.3}},
    {"slug": "f2_blend050", "price_lens_calibration": {"prior_range_blend": 0.5}},
    {
        "slug": "f2_flip_low",
        "price_lens_calibration": {"flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.25},
    },
    {
        "slug": "f2_ovn030_pr030",
        "price_lens_calibration": {"overnight_blend": 0.3, "prior_range_blend": 0.3},
    },
    {
        "slug": "f3_vol_dampen",
        "regime_conditional_price_dampen": {
            "enabled": True,
            "dampen_when_vol_regime_high": True,
            "vol_high_realized_5d": 0.03,
            "vol_high_price_mult": 0.6,
        },
        "vol_high_realized_5d": 0.03,
    },
    {
        "slug": "f2_flip_f3_vol",
        "price_lens_calibration": {"flip_to_bear_when_prior_range_low": True},
        "regime_conditional_price_dampen": {
            "enabled": True,
            "dampen_when_vol_regime_high": True,
            "vol_high_realized_5d": 0.03,
            "vol_high_price_mult": 0.6,
        },
        "vol_high_realized_5d": 0.03,
    },
    {
        "slug": "f2_flip_cbo_ovn",
        "price_lens_calibration": {"flip_to_bear_when_prior_range_low": True, "overnight_blend": 0.3},
        "conditional_bear_override": _CBO_OVN,
    },
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    for key in (
        "price_lens_calibration",
        "conditional_bear_override",
        "regime_conditional_price_dampen",
        "vol_high_realized_5d",
    ):
        if key in spec:
            rules[key] = spec[key]
    cfg["rules"] = rules
    return cfg


def _metrics(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hits": m.get("price_hits"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
    }


def _cohort(per: Path, wrong_dates: list[str]) -> dict[str, Any]:
    doc = _load(per)
    preds = {
        str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "").lower()
        for r in doc.get("rows") or []
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    return {
        "n_wrong_dates": len(wrong_dates),
        "n_bear_fix": sum(1 for ed in wrong_dates if preds.get(ed) == "bear"),
    }


def _run(slug: str, cfg: dict[str, Any], wrong_dates: list[str]) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    cfg_p = WORK / f"ens_{slug}.json"
    per = WORK / f"per_{slug}.json"
    score = WORK / f"score_{slug}.json"
    ev_out = WORK / f"eval_{slug}.json"
    cfg_p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    for cmd in [
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
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
            str(per.relative_to(ROOT)),
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
            str(ev_out.relative_to(ROOT)),
        ],
    ]:
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr or p.stdout)
    ev = _load(ev_out)
    return {
        "slug": slug,
        "metrics": _metrics(ev),
        "alert_1_pass": float((_metrics(ev).get("price_directional_hit_rate") or 0)) >= 0.5,
        "wrong_dir_cohort": _cohort(per, wrong_dates),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    wrong = list(_load(DEFAULT_CF).get("wrong_direction_dates") or []) if DEFAULT_CF.is_file() else []
    base = _load(DEFAULT_CFG)
    rows: list[dict[str, Any]] = []
    for spec in _VARIANTS:
        slug = str(spec["slug"])
        print(f"==> rfc_f2_f3 {slug}", file=sys.stderr)
        try:
            rows.append(_run(slug, _apply(base, spec), wrong))
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:400]})
    ok = [r for r in rows if "metrics" in r]
    best = max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    best_fix = max(ok, key=lambda r: int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0)) if ok else None
    report = {
        "schema": "btrack_rfc_f2_f3_experiment_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "rfc_source": "reports/btrack_price_lens_feature_rfc_v1_latest.json",
        "variants": rows,
        "best_by_headline": best,
        "best_by_wrong_dir_bear_fix": best_fix,
        "operator_lines": _ops(best, best_fix),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _ops(best: dict | None, fix: dict | None) -> list[str]:
    lines = ["- [MKM-RFC-F2F3] 30d F2 prior-range + F3 vol dampen sweep"]
    if best:
        m = best.get("metrics") or {}
        wc = best.get("wrong_dir_cohort") or {}
        lines.append(
            f"- [MKM-RFC-F2F3] best headline {best.get('slug')}: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"bear_fix={wc.get('n_bear_fix')}/7 A1={'pass' if best.get('alert_1_pass') else 'fail'}"
        )
    if fix and fix.get("slug") != (best or {}).get("slug"):
        wc = fix.get("wrong_dir_cohort") or {}
        m = fix.get("metrics") or {}
        lines.append(
            f"- [MKM-RFC-F2F3] best bear_fix {fix.get('slug')}: {wc.get('n_bear_fix')}/7 "
            f"all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    lines.append("- [MKM-RFC-F2F3] 180d OOS required before ensemble promote — run run_btrack_rfc_f2_f3_oos_180d_v1.py")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
