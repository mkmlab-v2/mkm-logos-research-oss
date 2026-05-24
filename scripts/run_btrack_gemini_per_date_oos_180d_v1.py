#!/usr/bin/env python3
"""[HYPO] Step 2: Gemini per-date 180d OOS vs prod baseline (cached API, min_conf gated for promotion)."""
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

DEFAULT_OUT = ROOT / "reports/btrack_gemini_per_date_oos_180d_v1_latest.json"
WORK = ROOT / "reports/btrack_gemini_per_date_oos_180d_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
ALERT_1 = 0.5
OOS_DAYS = 180


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _btc_metrics(ev_path: Path) -> dict[str, Any]:
    ev = _load(ev_path)
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    leg = (m.get("legs") or {}).get("btc") if isinstance(m.get("legs"), dict) else {}
    if not isinstance(leg, dict):
        leg = m
    headline = leg.get("price_directional_hit_rate") or m.get("price_directional_hit_rate")
    h = float(headline) if headline is not None else None
    return {
        "price_directional_hit_rate": h,
        "price_hit_rate_on_directional_calls": leg.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": leg.get("n_directional_calls"),
        "n_neutral_predictions": leg.get("n_neutral_predictions"),
        "n_evaluated": leg.get("n_evaluated"),
        "alert_1_pass": h is not None and h >= ALERT_1,
    }


def _pipeline_per_date(*, per_date: Path, tag: str, days: int) -> dict[str, Any]:
    score = WORK / f"score_{tag}_{days}d.json"
    ev_out = WORK / f"eval_{tag}_{days}d.json"
    p = _run(
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(days),
            "--force-dual-leg-panel",
            "--btc-csv",
            _rel(BTC),
            "--kospi-csv",
            _rel(KOSPI),
            "--per-date-direction-json",
            _rel(per_date),
            "--output",
            _rel(score),
        ]
    )
    if p.returncode != 0:
        return {"status": "failed", "step": "score", "stderr": (p.stderr or "")[-1500:]}
    p2 = _run(
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            _rel(score),
            "--output",
            _rel(ev_out),
        ]
    )
    if p2.returncode != 0:
        return {"status": "failed", "step": "eval", "stderr": (p2.stderr or "")[-1500:]}
    return {
        "status": "ok",
        "per_date": str(per_date),
        "score": str(score),
        "eval": str(ev_out),
        "metrics_btc": _btc_metrics(ev_out),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gemini-model", default="gemini-2.5-flash")
    ap.add_argument("--gemini-timeout", type=int, default=120)
    ap.add_argument("--sleep-sec", type=float, default=2.5)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument(
        "--skip-gemini-build",
        action="store_true",
        help="Reuse existing 180d raw+gated per-date under work dir",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    raw_per = WORK / "per_date_gemini_180d_raw.json"
    gated_per = WORK / "per_date_gemini_180d_gated.json"
    cache_dir = WORK / "gemini_per_date_cache_180d"

    steps: list[dict[str, Any]] = []

    if not args.skip_gemini_build and not args.dry_run:
        p = _run(
            [
                "scripts/build_btrack_gemini_per_date_directions_v1.py",
                "--recent-trading-days",
                str(OOS_DAYS),
                "--model",
                args.gemini_model,
                "--timeout",
                str(args.gemini_timeout),
                "--sleep-sec",
                str(args.sleep_sec),
                "--max-retries",
                str(args.max_retries),
                "--cache-dir",
                _rel(cache_dir),
                "--max-panel-days",
                str(OOS_DAYS),
                "--output",
                _rel(raw_per),
            ]
        )
        steps.append({"step": "gemini_build_180d", "exit_code": p.returncode})
        if p.returncode != 0:
            print(p.stderr or p.stdout, file=sys.stderr)
            return 1
        p2 = _run(
            [
                "scripts/apply_btrack_min_conf_to_per_date_directions_v1.py",
                "--input",
                _rel(raw_per),
                "--output",
                _rel(gated_per),
                "--ensemble-config",
                _rel(CFG),
            ]
        )
        steps.append({"step": "min_conf_gate", "exit_code": p2.returncode})
        if p2.returncode != 0:
            return 1

    if args.dry_run:
        report = {
            "schema": "btrack_gemini_per_date_oos_180d_v1",
            "dry_run": True,
            "oos_days": OOS_DAYS,
            "steps": steps,
        }
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"DRY-RUN plan: build {OOS_DAYS}d gemini + gate + score vs baseline")
        return 0

    if not gated_per.is_file() or not raw_per.is_file():
        print("Missing 180d per-date files; run without --skip-gemini-build", file=sys.stderr)
        return 2

    # prod baseline 180d (ensemble)
    cfg_copy = WORK / "ens_prod_180d.json"
    cfg_copy.write_text(CFG.read_text(encoding="utf-8"), encoding="utf-8")
    base_per = WORK / "per_date_prod_baseline_180d.json"
    p = _run(
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(OOS_DAYS),
            "--ensemble-config",
            _rel(cfg_copy),
            "--output",
            _rel(base_per),
        ]
    )
    if p.returncode != 0:
        print(p.stderr, file=sys.stderr)
        return 1

    prod_row = _pipeline_per_date(per_date=base_per, tag="prod", days=OOS_DAYS)
    gemini_raw_row = _pipeline_per_date(per_date=raw_per, tag="gemini_raw", days=OOS_DAYS)
    gemini_gated_row = _pipeline_per_date(per_date=gated_per, tag="gemini_gated", days=OOS_DAYS)

    prod_h = float((prod_row.get("metrics_btc") or {}).get("price_directional_hit_rate") or 0)
    gated_h = float((gemini_gated_row.get("metrics_btc") or {}).get("price_directional_hit_rate") or 0)
    delta = gated_h - prod_h

    if gated_h >= ALERT_1 and delta > 0:
        verdict = "holdout_review_required"
    elif delta > 0:
        verdict = "beats_prod_on_180d_alert1_fail"
    else:
        verdict = "reject_gemini_per_date_oos"

    report = {
        "schema": "btrack_gemini_per_date_oos_180d_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "oos_days": OOS_DAYS,
        "min_direction_confidence": 0.18,
        "steps": steps,
        "candidates": {
            "prod_baseline_180d": prod_row,
            "gemini_per_date_raw_180d": gemini_raw_row,
            "gemini_per_date_gated_180d": gemini_gated_row,
        },
        "promotion": {
            "headline_delta_gated_vs_prod": round(delta, 6),
            "verdict": verdict,
            "auto_promote": False,
        },
        "operator_lines": [
            "- [MKM-GEMINI-OOS-180] research_only; auto_promote=false.",
            f"- [MKM-GEMINI-OOS-180] prod={prod_h:.1%} gemini_gated={gated_h:.1%} delta={delta:+.1%}",
            f"- [MKM-GEMINI-OOS-180] verdict={verdict}",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
