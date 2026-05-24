#!/usr/bin/env python3
"""[HYPO] Step 1: Gemini per-date 30d raw vs min_conf-gated vs prod baseline (same eval ruler)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/btrack_gemini_fair_compare_v1_latest.json"
WORK = ROOT / "reports/btrack_model_swap_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
FROZEN_BASELINE = 0.366667
ALERT_1 = 0.5
DAYS = 30


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> None:
    p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{p.stderr or p.stdout}")


def _metrics_from_eval(path: Path) -> dict[str, Any]:
    ev = _load(path)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") if isinstance(m.get("legs"), dict) else {}
    if not isinstance(leg, dict):
        leg = m
    headline = leg.get("price_directional_hit_rate") or m.get("price_directional_hit_rate")
    dir_rate = leg.get("price_hit_rate_on_directional_calls") or m.get(
        "price_hit_rate_on_directional_calls"
    )
    n_dir = leg.get("n_directional_calls") or m.get("n_directional_calls")
    n_neu = leg.get("n_neutral_predictions") or m.get("n_neutral_predictions")
    h = float(headline) if headline is not None else None
    return {
        "price_directional_hit_rate": h,
        "price_hit_rate_on_directional_calls": dir_rate,
        "n_directional_calls": n_dir,
        "n_neutral_predictions": n_neu,
        "n_evaluated": leg.get("n_evaluated") or m.get("n_evaluated"),
        "alert_1_pass": h is not None and h >= ALERT_1,
        "beats_frozen_baseline": h is not None and h > FROZEN_BASELINE,
    }


def _score_eval(per_date: Path, tag: str) -> dict[str, Any]:
    score = WORK / f"score_fair_{tag}.json"
    ev_out = WORK / f"eval_fair_{tag}.json"
    _run(
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(DAYS),
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ]
    )
    _run(
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(ev_out.relative_to(ROOT)),
        ]
    )
    return {
        "per_date": str(per_date),
        "score": str(score),
        "eval": str(ev_out),
        "metrics": _metrics_from_eval(ev_out),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--gemini-per-date",
        type=Path,
        default=WORK / "per_date_gemini_per_date_30d.json",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.gemini_per_date.is_file():
        print(f"Missing gemini per-date panel: {args.gemini_per_date}", file=sys.stderr)
        return 2

    gated_path = WORK / "per_date_gemini_per_date_30d_minconf_gated.json"
    _run(
        [
            "scripts/apply_btrack_min_conf_to_per_date_directions_v1.py",
            "--input",
            str(args.gemini_per_date.relative_to(ROOT)),
            "--output",
            str(gated_path.relative_to(ROOT)),
            "--ensemble-config",
            str(CFG.relative_to(ROOT)),
        ]
    )

    baseline_per = WORK / "per_date_baseline_30d.json"
    if not baseline_per.is_file():
        _run(
            [
                "scripts/build_btrack_ensemble_per_date_directions_v1.py",
                "--recent-trading-days",
                str(DAYS),
                "--ensemble-config",
                str(CFG.relative_to(ROOT)),
                "--output",
                str(baseline_per.relative_to(ROOT)),
            ]
        )

    raw_row = _score_eval(args.gemini_per_date, "gemini_raw")
    gated_row = _score_eval(gated_path, "gemini_gated")
    base_row = _score_eval(baseline_per, "prod_baseline")

    report = {
        "schema": "btrack_gemini_fair_compare_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "window_days": DAYS,
        "min_direction_confidence": 0.18,
        "frozen_baseline_headline": FROZEN_BASELINE,
        "variants": {
            "prod_baseline_ensemble": base_row,
            "gemini_per_date_raw": raw_row,
            "gemini_per_date_min_conf_gated": gated_row,
        },
        "conclusion": {},
        "auto_promote": False,
    }
    gr = gated_row["metrics"]
    br = base_row["metrics"]
    report["conclusion"] = {
        "headline_delta_gated_vs_baseline": (
            (gr.get("price_directional_hit_rate") or 0) - (br.get("price_directional_hit_rate") or 0)
            if gr.get("price_directional_hit_rate") is not None
            else None
        ),
        "gated_beats_frozen_baseline": bool(gr.get("beats_frozen_baseline")),
        "gated_alert_1_pass": bool(gr.get("alert_1_pass")),
        "note": (
            "Raw gemini calls direction every day; gated applies prod min_conf=0.18 "
            "like local ensemble for apples-to-apples headline."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for k, v in report["variants"].items():
        m = v.get("metrics") or {}
        print(
            f"  {k}: headline={m.get('price_directional_hit_rate')} "
            f"dir_only={m.get('price_hit_rate_on_directional_calls')} "
            f"n_dir={m.get('n_directional_calls')} n_neu={m.get('n_neutral_predictions')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
