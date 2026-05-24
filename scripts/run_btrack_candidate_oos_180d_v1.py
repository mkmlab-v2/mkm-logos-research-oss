#!/usr/bin/env python3
"""180d OOS for promotion candidates vs production baseline (reports/ only)."""
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
DEFAULT_OUT = ROOT / "reports/btrack_candidate_oos_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_candidate_oos_180d_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
ALERT_1_FLOOR = 0.5

_CBO_OVN = {
    "enabled": True,
    "when": {
        "price_score_min": 0.03,
        "overnight_negative": True,
        "weighted_min": 0.03,
    },
    "action": "negate_weighted",
}

CANDIDATES: list[dict[str, Any]] = [
    {"slug": "prod_baseline", "label": "production min_conf=0.18"},
    {"slug": "cbo_overnight", "conditional_bear_override": _CBO_OVN},
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_variant(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    for key in ("price_lens_calibration", "conditional_bear_override", "regime_conditional_price_dampen"):
        if key in spec:
            rules[key] = spec[key]
    cfg["rules"] = rules
    return cfg


def _btc_leg(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") or m
    return {
        "price_directional_hit_rate": leg.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": leg.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": leg.get("n_directional_calls") or m.get("n_directional_calls"),
        "n_neutral_predictions": leg.get("n_neutral_predictions") or m.get("n_neutral_predictions"),
        "price_hits": leg.get("price_hits") or m.get("price_hits"),
        "n_evaluated": leg.get("n_evaluated") or m.get("n_evaluated"),
    }


def _run_180d(slug: str, cfg: dict[str, Any], n: int) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    cfg_p = WORK / f"ens_{slug}_{n}d.json"
    per = WORK / f"per_{slug}_{n}d.json"
    score = WORK / f"score_{slug}_{n}d.json"
    ev_out = WORK / f"eval_{slug}_{n}d.json"
    cfg_p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    for cmd in [
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(n),
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(n),
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
            raise RuntimeError(f"{' '.join(cmd)}\n{p.stderr or p.stdout}")
    ev = _load(ev_out)
    return {
        "slug": slug,
        "paths": {
            "per_date": str(per.resolve()),
            "score": str(score.resolve()),
            "eval": str(ev_out.resolve()),
        },
        "metrics_btc_180d": _btc_leg(ev),
        "alert_1_pass": float((_btc_leg(ev).get("price_directional_hit_rate") or 0)) >= ALERT_1_FLOOR,
    }


def _wrong_dir_on_30d_subset(per_date_path: Path, wrong_dates: list[str]) -> dict[str, Any]:
    doc = _load(per_date_path)
    preds = {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    in_window = [ed for ed in wrong_dates if ed in preds]
    bear_fix = sum(1 for ed in in_window if preds.get(ed) == "bear")
    return {
        "wrong_dir_dates_in_panel": in_window,
        "n_bear_fix": bear_fix,
        "n_wrong_dir": len(in_window),
    }


def _promotion_decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = next((r for r in rows if r.get("slug") == "prod_baseline"), rows[0] if rows else {})
    base_rate = float((base.get("metrics_btc_180d") or {}).get("price_directional_hit_rate") or 0)
    best = None
    for r in rows:
        if r.get("slug") == "prod_baseline":
            continue
        rate = float((r.get("metrics_btc_180d") or {}).get("price_directional_hit_rate") or 0)
        if rate >= base_rate and r.get("alert_1_pass"):
            best = r
    if best:
        verdict = "candidate_beat_baseline_on_180d_and_alert1"
        promote = False  # still need human + holdout policy
    else:
        verdict = "reject_all_candidates"
        promote = False
    return {
        "verdict": verdict,
        "auto_promote": promote,
        "baseline_180d_all_rows": base_rate,
        "note": "auto_promote always false; human review + docs/final artifacts unchanged by this script.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    n = int(args.recent_trading_days)
    if not BUNDLE.is_file() or not BTC_CSV.is_file():
        print("Missing bundle or BTC CSV.", file=sys.stderr)
        return 2

    wrong_dates = list(_load(DEFAULT_CF).get("wrong_direction_dates") or []) if DEFAULT_CF.is_file() else []
    base_cfg = _load(DEFAULT_CFG)
    results: list[dict[str, Any]] = []
    for spec in CANDIDATES:
        slug = str(spec["slug"])
        print(f"==> OOS {n}d {slug}", file=sys.stderr)
        try:
            row = _run_180d(slug, _apply_variant(base_cfg, spec), n)
            row["label"] = spec.get("label", slug)
            per_30 = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"
            if wrong_dates and per_30.is_file() and slug == "prod_baseline":
                row["wrong_dir_30d_cohort"] = _wrong_dir_on_30d_subset(per_30, wrong_dates)
            elif wrong_dates:
                row["wrong_dir_30d_cohort"] = _wrong_dir_on_30d_subset(
                    Path(row["paths"]["per_date"]), wrong_dates
                )
            results.append(row)
        except RuntimeError as e:
            results.append({"slug": slug, "error": str(e)[:500]})

    decision = _promotion_decision([r for r in results if "metrics_btc_180d" in r])
    prod_30 = _load(ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json")
    m30 = prod_30.get("metrics") or {}
    report = {
        "schema": "btrack_candidate_oos_180d_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "recent_trading_days": n,
        "alert_1_floor": ALERT_1_FLOOR,
        "production_30d_snapshot": {
            "price_directional_hit_rate": m30.get("price_directional_hit_rate"),
            "alert_1_pass": float(m30.get("price_directional_hit_rate") or 0) >= ALERT_1_FLOOR,
        },
        "candidates": results,
        "promotion_decision": decision,
        "operator_lines": _operator_lines(results, decision, m30),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _operator_lines(results: list[dict[str, Any]], decision: dict[str, Any], m30: dict[str, Any]) -> list[str]:
    lines = [
        f"- [MKM-OOS-180D] prod 30d all-rows {float(m30.get('price_directional_hit_rate') or 0):.1%} "
        f"(ALERT_1={'pass' if float(m30.get('price_directional_hit_rate') or 0) >= ALERT_1_FLOOR else 'fail'})"
    ]
    for r in results:
        if "metrics_btc_180d" not in r:
            continue
        m = r["metrics_btc_180d"]
        wc = r.get("wrong_dir_30d_cohort") or {}
        lines.append(
            f"- [MKM-OOS-180D] {r.get('slug')}: 180d all-rows "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"dir-only {float(m.get('price_hit_rate_on_directional_calls') or 0):.1%} "
            f"bear_fix_30d={wc.get('n_bear_fix')}/{wc.get('n_wrong_dir')} "
            f"A1={'pass' if r.get('alert_1_pass') else 'fail'}"
        )
    lines.append(f"- [MKM-OOS-180D] decision: {decision.get('verdict')} auto_promote={decision.get('auto_promote')}")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
