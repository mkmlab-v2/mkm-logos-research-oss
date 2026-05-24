#!/usr/bin/env python3
"""[HYPO] Sweep v1 ensemble margin / price weight for BTC headline all-rows hit rate.

Does not auto-write production config. Writes reports/btrack_v1_headline_tune_sweep_v1_latest.json.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BASELINE_EVAL = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_v1_headline_tune_sweep_v1_latest.json"
WORK = ROOT / "reports/btrack_v1_headline_tune_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_btc(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") or {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "price_hits": m.get("price_hits"),
        "btc_leg_hit_rate": leg.get("price_directional_hit_rate"),
    }


def _reweight_price(weights: dict[str, float], price_target: float) -> dict[str, float]:
    w = {k: float(v) for k, v in weights.items()}
    price_target = max(0.05, min(0.90, price_target))
    others = {k: v for k, v in w.items() if k != "price"}
    s = sum(others.values()) or 1.0
    scale = (1.0 - price_target) / s
    out = {k: v * scale for k, v in others.items()}
    out["price"] = price_target
    return out


def _run_variant(
    *,
    slug: str,
    cfg: dict[str, Any],
    work_dir: Path,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = work_dir / f"ensemble_{slug}.json"
    per_date = work_dir / f"per_date_{slug}.json"
    score = work_dir / f"score_{slug}.json"
    eval_out = work_dir / f"eval_{slug}.json"

    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}

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
    return {
        "slug": slug,
        "tie_break_min_margin": rules.get("tie_break_min_margin"),
        "weights": cfg.get("weights"),
        "metrics": _metrics_btc(ev),
        "alert_1_pass": float((ev.get("metrics") or {}).get("price_directional_hit_rate") or 0) >= 0.5,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--margins", default="0.02,0.025,0.03,0.035,0.04")
    ap.add_argument("--price-weights", default="0.60,0.65,0.70,0.75")
    ap.add_argument("--baseline-eval", type=Path, default=DEFAULT_BASELINE_EVAL)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-runs", type=int, default=0, help="0 = all combinations")
    args = ap.parse_args()

    if not BUNDLE.is_file() or not BTC_CSV.is_file():
        print("Missing bundle or BTC CSV.", file=sys.stderr)
        return 2

    base_cfg = _load(args.ensemble_config)
    base_weights = dict(base_cfg.get("weights") or {})
    margins = [float(x.strip()) for x in args.margins.split(",") if x.strip()]
    price_ws = [float(x.strip()) for x in args.price_weights.split(",") if x.strip()]

    baseline_m = _metrics_btc(_load(args.baseline_eval)) if args.baseline_eval.is_file() else {}
    rows: list[dict[str, Any]] = []
    n = 0
    for margin in margins:
        for pw in price_ws:
            if args.max_runs and n >= args.max_runs:
                break
            cfg = copy.deepcopy(base_cfg)
            rules = dict(cfg.get("rules") or {})
            rules["tie_break_min_margin"] = margin
            cfg["rules"] = rules
            cfg["weights"] = _reweight_price(base_weights, pw)
            slug = f"m{margin:.3f}_p{pw:.2f}".replace(".", "")
            print(f"==> tune {slug}", file=sys.stderr)
            try:
                row = _run_variant(slug=slug, cfg=cfg, work_dir=WORK)
                rows.append(row)
            except RuntimeError as e:
                rows.append({"slug": slug, "error": str(e)[:500]})
            n += 1

    ok_rows = [r for r in rows if "metrics" in r]
    best = (
        max(
            ok_rows,
            key=lambda r: float((r.get("metrics") or {}).get("price_directional_hit_rate") or 0),
        )
        if ok_rows
        else None
    )
    report = {
        "schema": "btrack_v1_headline_tune_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "baseline_metrics": baseline_m,
        "candidates": rows,
        "best_by_headline_all_rows": best,
        "alert_1_floor": 0.5,
        "note": "30d in-sample sweep; human review before promoting margin/weights to btrack_lens_ensemble_v1.json.",
        "operator_lines": _operator_lines(baseline_m, best),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        print(line)
    return 0


def _operator_lines(baseline: dict[str, Any], best: dict[str, Any] | None) -> list[str]:
    lines = [
        (
            f"- [MKM-HEADLINE-TUNE] baseline: all-rows {float(baseline.get('price_directional_hit_rate') or 0):.1%} "
            f"calls={baseline.get('n_directional_calls')}"
        )
    ]
    if best and best.get("metrics"):
        m = best["metrics"]
        lines.append(
            f"- [MKM-HEADLINE-TUNE] best sweep {best.get('slug')}: all-rows {float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"margin={best.get('tie_break_min_margin')} price_w={best.get('weights', {}).get('price')} "
            f"A1={'pass' if best.get('alert_1_pass') else 'fail'}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
