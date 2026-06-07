#!/usr/bin/env python3
"""[HYPO] Sweep margin / min_conf / neutral_penalty for neutral-abstain cohort (30d)."""
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
DEFAULT_MISS = ROOT / "reports/btrack_headline_miss_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_neutral_abstain_margin_experiment_v1_latest.json"
WORK = ROOT / "reports/btrack_neutral_margin_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline"},
    {"slug": "margin_015", "tie_break_min_margin": 0.015},
    {"slug": "margin_020", "tie_break_min_margin": 0.02},
    {"slug": "margin_025", "tie_break_min_margin": 0.025},
    {"slug": "min_conf_017", "min_direction_confidence": 0.17},
    {"slug": "min_conf_016", "min_direction_confidence": 0.16},
    {"slug": "neutral_pen_m05", "neutral_penalty": -0.05},
    {"slug": "margin020_min017", "tie_break_min_margin": 0.02, "min_direction_confidence": 0.17},
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _neutral_miss_days(miss_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        m
        for m in (miss_doc.get("misses") or [])
        if isinstance(m, dict) and m.get("miss_kind") == "neutral_abstain_miss"
    ]


def _apply(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    if "tie_break_min_margin" in spec:
        rules["tie_break_min_margin"] = spec["tie_break_min_margin"]
    if "min_direction_confidence" in spec:
        rules["min_direction_confidence"] = spec["min_direction_confidence"]
    if "neutral_penalty" in spec:
        rules["neutral_penalty"] = spec["neutral_penalty"]
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


def _run(slug: str, cfg: dict[str, Any], *, recent_trading_days: int) -> dict[str, Any]:
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
            str(recent_trading_days),
            "--ensemble-config",
            str(cfg_p.relative_to(ROOT)),
            "--output",
            str(per.relative_to(ROOT)),
        ],
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(recent_trading_days),
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
    return {"slug": slug, "per_date_path": str(per.resolve()), "eval": _load(ev_out)}


def _cohort_recovery(per_date_path: Path, cohort: list[dict[str, Any]]) -> dict[str, Any]:
    doc = _load(per_date_path)
    preds = {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    recovered = 0
    newly_directional = 0
    per_day: list[dict[str, Any]] = []
    for m in cohort:
        ed = str(m.get("eval_date"))[:10]
        actual = str(m.get("actual_direction") or "").lower()
        baseline_pred = str(m.get("predicted_direction") or "").lower()
        pred = preds.get(ed, "neutral")
        hit = pred == actual
        if pred in ("bull", "bear"):
            newly_directional += 1
            if hit:
                recovered += 1
        per_day.append(
            {
                "eval_date": ed,
                "baseline_predicted": baseline_pred,
                "variant_predicted": pred,
                "actual_direction": actual,
                "newly_directional": pred in ("bull", "bear") and baseline_pred == "neutral",
                "hit": hit,
            }
        )
    return {
        "n_cohort": len(cohort),
        "n_newly_directional": newly_directional,
        "n_recovered_hits": recovered,
        "per_day": per_day,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--miss-report", type=Path, default=DEFAULT_MISS)
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=30,
        help="Per-date rebuild window; use 180 when miss cohort includes holdout7 dates.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.miss_report.is_file():
        print(f"Missing miss report: {args.miss_report}", file=sys.stderr)
        return 2
    miss_doc = _load(args.miss_report)
    cohort = _neutral_miss_days(miss_doc)
    base = _load(DEFAULT_CFG)
    rows: list[dict[str, Any]] = []
    for spec in VARIANTS:
        slug = str(spec["slug"])
        print(f"==> neutral_margin {slug}", file=sys.stderr)
        try:
            raw = _run(slug, _apply(base, spec), recent_trading_days=args.recent_trading_days)
            ev = raw["eval"]
            row = {
                "slug": slug,
                "rules": _apply(base, spec).get("rules"),
                "metrics": _metrics(ev),
                "alert_1_pass": float((_metrics(ev).get("price_directional_hit_rate") or 0)) >= 0.5,
                "neutral_abstain_cohort": _cohort_recovery(Path(raw["per_date_path"]), cohort),
            }
            rows.append(row)
        except RuntimeError as e:
            rows.append({"slug": slug, "error": str(e)[:400]})

    ok = [r for r in rows if "metrics" in r]
    best_a1 = max(ok, key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0)) if ok else None
    best_rec = (
        max(ok, key=lambda r: int((r.get("neutral_abstain_cohort") or {}).get("n_recovered_hits") or 0)) if ok else None
    )
    report = {
        "schema": "btrack_neutral_abstain_margin_experiment_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "miss_report_path": str(args.miss_report.resolve()),
        "recent_trading_days": args.recent_trading_days,
        "n_neutral_abstain_cohort": len(cohort),
        "variants": rows,
        "best_by_headline": best_a1,
        "best_by_cohort_recovery": best_rec,
        "promotion_note": "Do not lower production min_conf below 0.18 without holdout; margin-only changes preferred for research.",
        "operator_lines": _ops(ok, best_a1, best_rec, len(cohort)),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _ops(ok: list[dict[str, Any]], best_a1: dict | None, best_rec: dict | None, n: int) -> list[str]:
    lines = [f"- [MKM-NEUTRAL-MARGIN] cohort n={n} neutral_abstain misses"]
    if best_a1:
        m = best_a1.get("metrics") or {}
        c = best_a1.get("neutral_abstain_cohort") or {}
        lines.append(
            f"- [MKM-NEUTRAL-MARGIN] best headline {best_a1.get('slug')}: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"recovered={c.get('n_recovered_hits')}/{n} A1={'pass' if best_a1.get('alert_1_pass') else 'fail'}"
        )
    if best_rec and best_rec.get("slug") != (best_a1 or {}).get("slug"):
        c = best_rec.get("neutral_abstain_cohort") or {}
        m = best_rec.get("metrics") or {}
        lines.append(
            f"- [MKM-NEUTRAL-MARGIN] best recovery {best_rec.get('slug')}: "
            f"recovered={c.get('n_recovered_hits')}/{n} all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    lines.append("- [MKM-NEUTRAL-MARGIN] hold prod min_conf=0.18 unless holdout passes")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
