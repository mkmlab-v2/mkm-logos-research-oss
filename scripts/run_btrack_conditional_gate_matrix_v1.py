#!/usr/bin/env python3
"""[HYPO] Conditional gate matrix: F1 overnight x F2 prior-range x last_ret (30d + optional 180d)."""
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
DEFAULT_OUT = ROOT / "reports/btrack_conditional_gate_matrix_v1_latest.json"
WORK = ROOT / "reports/btrack_cond_gate_matrix_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

_WHEN_BASE = {
    "price_score_min": 0.03,
    "weighted_min": 0.03,
}
_CBO = {"enabled": True, "when": dict(_WHEN_BASE), "action": "negate_weighted"}


def _cbo(**when_extra: Any) -> dict[str, Any]:
    w = dict(_WHEN_BASE)
    w.update(when_extra)
    return {"enabled": True, "when": w, "action": "negate_weighted"}


MATRIX: list[dict[str, Any]] = [
    {"slug": "baseline"},
    {"slug": "cbo_last_neg", "conditional_bear_override": _cbo()},
    {"slug": "cbo_ovn", "conditional_bear_override": _cbo(overnight_negative=True)},
    {
        "slug": "cbo_ovn_pr25",
        "conditional_bear_override": _cbo(overnight_negative=True, prior_range_low=True, prior_range_low_max=0.25),
    },
    {
        "slug": "cbo_ovn_pr35",
        "conditional_bear_override": _cbo(overnight_negative=True, prior_range_low=True, prior_range_low_max=0.35),
    },
    {
        "slug": "cbo_pr25_only",
        "conditional_bear_override": _cbo(prior_range_low=True, prior_range_low_max=0.25),
    },
    {
        "slug": "cbo_ovn_last_pr25",
        "conditional_bear_override": _cbo(
            overnight_negative=True,
            prior_range_low=True,
            prior_range_low_max=0.25,
        ),
    },
    {
        "slug": "cbo_ovn_macro_bull",
        "conditional_bear_override": _cbo(overnight_negative=True, require_macro_bull=True, macro_score_min=0.0),
    },
    {
        "slug": "cbo_halve_ovn_pr25",
        "conditional_bear_override": {
            "enabled": True,
            "when": {
                **_WHEN_BASE,
                "overnight_negative": True,
                "prior_range_low": True,
                "prior_range_low_max": 0.25,
            },
            "action": "halve_and_negate",
        },
    },
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    if "conditional_bear_override" in spec:
        rules["conditional_bear_override"] = spec["conditional_bear_override"]
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
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    preds = {
        str(r["eval_date"])[:10]: str(r.get("predicted_direction") or "").lower()
        for r in rows
        if str(r.get("instrument") or "").lower() == "btc"
    }
    cbo_days = [
        str(r["eval_date"])[:10]
        for r in rows
        if str(r.get("instrument") or "").lower() == "btc" and r.get("conditional_bear_override_applied")
    ]
    return {
        "n_wrong_dates": len(wrong_dates),
        "n_bear_fix": sum(1 for ed in wrong_dates if preds.get(ed) == "bear"),
        "n_cbo_fired": len(cbo_days),
        "cbo_fired_on_wrong_dir": sum(1 for ed in wrong_dates if ed in cbo_days),
    }


def _run(slug: str, cfg: dict[str, Any], wrong_dates: list[str], days: int) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    cfg_p = WORK / f"ens_{slug}_{days}d.json"
    per = WORK / f"per_{slug}_{days}d.json"
    score = WORK / f"score_{slug}_{days}d.json"
    ev_out = WORK / f"eval_{slug}_{days}d.json"
    cfg_p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    for cmd in [
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(days),
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(days),
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
    rate = float((_metrics(ev).get("price_directional_hit_rate") or 0))
    return {
        "slug": slug,
        "metrics": _metrics(ev),
        "alert_1_pass": rate >= 0.5,
        "wrong_dir_cohort": _cohort(per, wrong_dates),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--also-180d", action="store_true", help="Run 180d OOS for top bear_fix variants")
    args = ap.parse_args()
    wrong = list(_load(DEFAULT_CF).get("wrong_direction_dates") or []) if DEFAULT_CF.is_file() else []
    base = _load(DEFAULT_CFG)
    rows: list[dict[str, Any]] = []
    for spec in MATRIX:
        slug = str(spec["slug"])
        print(f"==> gate_matrix {slug} {args.days}d", file=sys.stderr)
        try:
            rows.append(_run(slug, _apply(base, spec), wrong, args.days))
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:400]})
    ok = [r for r in rows if "metrics" in r]
    prod_rate = 0.366667 if args.days == 30 else None
    if ok:
        bl = next((r for r in ok if r["slug"] == "baseline"), ok[0])
        prod_rate = float((bl.get("metrics") or {}).get("price_directional_hit_rate") or 0)
    best_h = max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    best_fix = max(ok, key=lambda r: int((r.get("wrong_dir_cohort") or {}).get("n_bear_fix") or 0)) if ok else None
    oos_180: list[dict[str, Any]] = []
    if args.also_180d and ok:
        slugs = {best_fix.get("slug")} if best_fix else set()
        if best_h:
            slugs.add(best_h.get("slug"))
        slugs.add("cbo_ovn_pr25")
        slugs.discard("baseline")
        for spec in MATRIX:
            if spec["slug"] not in slugs:
                continue
            slug = str(spec["slug"])
            print(f"==> gate_matrix_oos {slug} 180d", file=sys.stderr)
            try:
                oos_180.append(_run(slug, _apply(base, spec), wrong, 180))
            except RuntimeError as e:
                oos_180.append({"slug": slug, "error": str(e)[:400]})
    report = {
        "schema": "btrack_conditional_gate_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "n_trading_days": args.days,
        "production_baseline_all_rows": prod_rate,
        "matrix": rows,
        "best_by_headline": best_h,
        "best_by_wrong_dir_bear_fix": best_fix,
        "oos_180d_candidates": oos_180 if args.also_180d else None,
        "operator_lines": _ops(prod_rate, best_h, best_fix, oos_180),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _ops(
    prod: float | None,
    best_h: dict | None,
    best_fix: dict | None,
    oos: list[dict[str, Any]],
) -> list[str]:
    lines = [f"- [MKM-GATE-MATRIX] conditional F1×F2×CBO sweep (prod ref {prod:.1%})" if prod else "- [MKM-GATE-MATRIX] sweep"]
    if best_h:
        m = best_h.get("metrics") or {}
        wc = best_h.get("wrong_dir_cohort") or {}
        lines.append(
            f"- [MKM-GATE-MATRIX] best headline {best_h.get('slug')}: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"bear_fix={wc.get('n_bear_fix')}/7 cbo_fires={wc.get('n_cbo_fired')} A1={'pass' if best_h.get('alert_1_pass') else 'fail'}"
        )
    if best_fix and best_fix.get("slug") != (best_h or {}).get("slug"):
        wc = best_fix.get("wrong_dir_cohort") or {}
        m = best_fix.get("metrics") or {}
        lines.append(
            f"- [MKM-GATE-MATRIX] best bear_fix {best_fix.get('slug')}: {wc.get('n_bear_fix')}/7 "
            f"on_wrong={wc.get('cbo_fired_on_wrong_dir')} all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    for r in oos:
        if "metrics" not in r:
            continue
        m = r.get("metrics") or {}
        lines.append(
            f"- [MKM-GATE-MATRIX-OOS] {r.get('slug')} 180d: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} A1={'pass' if r.get('alert_1_pass') else 'fail'}"
        )
    lines.append("- [MKM-GATE-MATRIX] no production promote without 180d ALERT_1 pass + headline >= prod 30d")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
