#!/usr/bin/env python3
"""180d OOS for RFC F2/F3 top candidates vs production baseline."""
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
DEFAULT_30D = ROOT / "reports/btrack_rfc_f2_f3_experiment_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_rfc_f2_f3_oos_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_rfc_f2_f3_oos_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
ALERT_1_FLOOR = 0.5
DAYS = 180

_CBO_OVN = {
    "enabled": True,
    "when": {
        "price_score_min": 0.03,
        "overnight_negative": True,
        "weighted_min": 0.03,
    },
    "action": "negate_weighted",
}

# Slugs to OOS after 30d sweep (baseline always).
CANDIDATE_SPECS: list[dict[str, Any]] = [
    {"slug": "prod_baseline"},
    {
        "slug": "f2_flip_low",
        "price_lens_calibration": {"flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.25},
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


def _btc_metrics(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") if isinstance(m.get("legs"), dict) else None
    src = leg if isinstance(leg, dict) else m
    return {
        "price_directional_hit_rate": src.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": src.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": src.get("n_directional_calls") or m.get("n_directional_calls"),
        "n_neutral_predictions": src.get("n_neutral_predictions") or m.get("n_neutral_predictions"),
        "price_hits": src.get("price_hits") or m.get("price_hits"),
        "n_evaluated": src.get("n_evaluated") or m.get("n_evaluated"),
    }


def _run(slug: str, cfg: dict[str, Any]) -> dict[str, Any]:
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
            str(DAYS),
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(DAYS),
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
    rate = float(_btc_metrics(ev).get("price_directional_hit_rate") or 0)
    return {
        "slug": slug,
        "metrics_180d_btc": _btc_metrics(ev),
        "alert_1_pass": rate >= ALERT_1_FLOOR,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--experiment-30d", type=Path, default=DEFAULT_30D)
    args = ap.parse_args()
    base = _load(DEFAULT_CFG)
    specs = list(CANDIDATE_SPECS)
    if args.experiment_30d.is_file():
        exp = _load(args.experiment_30d)
        best = exp.get("best_by_headline") or {}
        best_slug = str(best.get("slug") or "")
        if best_slug and best_slug not in {s["slug"] for s in specs}:
            for v in exp.get("variants") or []:
                if isinstance(v, dict) and v.get("slug") == best_slug:
                    specs.append({"slug": f"30d_best_{best_slug}", **_pick_spec_keys(v)})
                    break
    rows: list[dict[str, Any]] = []
    for spec in specs:
        slug = str(spec["slug"])
        print(f"==> rfc_f2_f3_oos {slug}", file=sys.stderr)
        try:
            rows.append(_run(slug, _apply(base, spec)))
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:400]})
    ok = [r for r in rows if "metrics_180d_btc" in r]
    prod = next((r for r in ok if r.get("slug") == "prod_baseline"), None)
    prod_rate = float((prod or {}).get("metrics_180d_btc", {}).get("price_directional_hit_rate") or 0)
    passed = [r for r in ok if r.get("alert_1_pass")]
    best = max(ok, key=lambda r: float((r.get("metrics_180d_btc") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    verdict = "reject_all_candidates" if not passed else "holdout_review_required"
    report = {
        "schema": "btrack_rfc_f2_f3_oos_180d_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "alert_1_floor": ALERT_1_FLOOR,
        "n_trading_days": DAYS,
        "prod_baseline_180d_all_rows": prod_rate,
        "candidates": rows,
        "alert_1_pass_slugs": [r["slug"] for r in passed],
        "best_by_180d_headline": best,
        "verdict": verdict,
        "auto_promote": False,
        "operator_lines": _ops(prod_rate, best, passed, verdict),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _pick_spec_keys(v: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("price_lens_calibration", "conditional_bear_override", "regime_conditional_price_dampen"):
        if k in v:
            out[k] = v[k]
    return out


def _ops(prod: float, best: dict | None, passed: list, verdict: str) -> list[str]:
    lines = [f"- [MKM-RFC-F2F3-OOS] prod 180d all-rows {prod:.1%} (floor 50%)"]
    if best:
        m = best.get("metrics_180d_btc") or {}
        lines.append(
            f"- [MKM-RFC-F2F3-OOS] best 180d {best.get('slug')}: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"A1={'pass' if best.get('alert_1_pass') else 'fail'}"
        )
    lines.append(f"- [MKM-RFC-F2F3-OOS] verdict={verdict} pass_count={len(passed)} auto_promote=False")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
