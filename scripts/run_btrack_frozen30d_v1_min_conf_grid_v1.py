#!/usr/bin/env python3
"""[HYPO] v1 per-date + min_direction_confidence grid on frozen KPI-A anchor dates (BTC).

Does not modify production *_latest.json. B-track research only; no Track A / live auto-promote.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
BASELINE_EVAL = ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/btrack_frozen30d_v1_min_conf_grid_v1_latest.json"
WORK = ROOT / "reports/btrack_frozen30d_v1_min_conf_grid_work"
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(ev: dict[str, Any]) -> dict[str, Any]:
    m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "price_hit_rate_on_directional_calls": m.get("price_hit_rate_on_directional_calls"),
        "n_evaluated": m.get("n_evaluated"),
        "n_directional_calls": m.get("n_directional_calls"),
        "n_neutral_predictions": m.get("n_neutral_predictions"),
        "price_hits": m.get("price_hits"),
        "directional_call_hits": m.get("directional_call_hits"),
        "headline_instrument": m.get("headline_instrument"),
    }


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{proc.stderr or proc.stdout}")


def _anchor_dates(score_path: Path) -> list[str]:
    doc = _load(score_path)
    dates = sorted(
        {
            str(r.get("eval_date") or "")[:10]
            for r in (doc.get("rows") or [])
            if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
        }
    )
    return [d for d in dates if d]


def _run_lane(
    *,
    min_conf: float,
    dates_path: Path,
    anchor_score: Path,
    work_dir: Path,
) -> dict[str, Any]:
    slug = str(min_conf).replace(".", "p")
    per_date = work_dir / f"per_date_v1_minconf_{slug}.json"
    score_out = work_dir / f"score_minconf_{slug}.json"
    eval_out = work_dir / f"eval_minconf_{slug}.json"
    env = os.environ.copy()
    env["MKM_BTRACK_MIN_DIRECTION_CONFIDENCE"] = str(min_conf)
    py = sys.executable
    _run(
        [
            py,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--score-json",
            str(anchor_score.relative_to(ROOT)),
            "--ensemble-mode",
            "v1",
            "--output",
            str(per_date.relative_to(ROOT)),
        ],
        env=env,
    )
    _run(
        [
            py,
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--btc-csv",
            str(BTC_CSV.relative_to(ROOT)),
            "--batch-eval-dates-json",
            str(dates_path.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date.relative_to(ROOT)),
            "--output",
            str(score_out.relative_to(ROOT)),
        ],
        env=env,
    )
    _run(
        [
            py,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_out.relative_to(ROOT)),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_out.relative_to(ROOT)),
        ],
        env=env,
    )
    per_doc = _load(per_date)
    n_neutral = sum(
        1
        for r in (per_doc.get("rows") or [])
        if isinstance(r, dict)
        and str(r.get("predicted_direction") or "").lower() in ("neutral", "abstain")
    )
    gated = (per_doc.get("gate_meta") or {}).get("rows_gated_to_neutral")
    if gated is None:
        gated = sum(
            1
            for r in (per_doc.get("rows") or [])
            if isinstance(r, dict)
            and (r.get("low_confidence_direction_gate") or {}).get("applied")
        )
    m = _metrics(_load(eval_out))
    hr = float(m.get("price_directional_hit_rate") or 0)
    return {
        "min_direction_confidence": min_conf,
        "metrics": m,
        "n_per_date_neutral": n_neutral,
        "rows_gated_to_neutral": gated,
        "alert_1_pass_50pct": hr >= 0.5,
        "paths": {
            "per_date_json": str(per_date),
            "score_json": str(score_out),
            "eval_json": str(eval_out),
        },
    }


def _parse_grid(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.append(max(0.0, min(1.0, float(part))))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor-score", type=Path, default=ANCHOR_SCORE)
    ap.add_argument("--baseline-eval", type=Path, default=BASELINE_EVAL)
    ap.add_argument(
        "--grid",
        default="0.08,0.10,0.12,0.14,0.16,0.18,0.20,0.22,0.25,0.28,0.32,0.35",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--work-dir", type=Path, default=WORK)
    ap.add_argument(
        "--run-promotion-gates-on-best",
        action="store_true",
        help="Run recommended eval chain (180d WF) for best all-rows threshold; writes gates JSON.",
    )
    args = ap.parse_args()

    if not args.anchor_score.is_file():
        print(f"Missing anchor score: {args.anchor_score}", file=sys.stderr)
        return 2
    if not args.baseline_eval.is_file():
        print(f"Missing baseline eval: {args.baseline_eval}", file=sys.stderr)
        return 2
    if not BTC_CSV.is_file():
        print(f"Missing BTC CSV: {BTC_CSV}", file=sys.stderr)
        return 2

    dates = _anchor_dates(args.anchor_score)
    if not dates:
        print("No BTC eval_dates in anchor score.", file=sys.stderr)
        return 2

    args.work_dir.mkdir(parents=True, exist_ok=True)
    dates_path = args.work_dir / "anchor_eval_dates.json"
    dates_path.write_text(json.dumps({"eval_dates": dates}, indent=2) + "\n", encoding="utf-8")

    base_m = _metrics(_load(args.baseline_eval))
    grid = _parse_grid(args.grid)
    candidates: list[dict[str, Any]] = []
    for t in grid:
        print(f"==> frozen30d v1 min_conf={t:.2f}", file=sys.stderr)
        candidates.append(
            _run_lane(
                min_conf=t,
                dates_path=dates_path,
                anchor_score=args.anchor_score,
                work_dir=args.work_dir,
            )
        )

    def _score(c: dict[str, Any]) -> tuple[float, float, int]:
        m = c["metrics"]
        return (
            float(m.get("price_directional_hit_rate") or 0),
            float(m.get("price_hit_rate_on_directional_calls") or 0),
            int(m.get("n_directional_calls") or 0),
        )

    best = max(candidates, key=_score) if candidates else None
    rows = []
    for c in candidates:
        cm = c["metrics"]
        bm = base_m
        rows.append(
            {
                **c,
                "delta_vs_frozen_kpi_a": {
                    "price_directional_hit_rate": round(
                        float(cm.get("price_directional_hit_rate") or 0)
                        - float(bm.get("price_directional_hit_rate") or 0),
                        6,
                    ),
                    "n_directional_calls": int(cm.get("n_directional_calls") or 0)
                    - int(bm.get("n_directional_calls") or 0),
                    "n_neutral_predictions": int(cm.get("n_neutral_predictions") or 0)
                    - int(bm.get("n_neutral_predictions") or 0),
                },
            }
        )

    gates_block: dict[str, Any] | None = None
    if best and args.run_promotion_gates_on_best:
        bt = float(best["min_direction_confidence"])
        per_best = Path(best["paths"]["per_date_json"])
        gates_out = args.work_dir / f"promotion_gates_best_minconf_{str(bt).replace('.', 'p')}.json"
        summary_out = args.work_dir / f"recommended_chain_summary_best_minconf_{str(bt).replace('.', 'p')}.json"
        env = os.environ.copy()
        env["MKM_BTRACK_MIN_DIRECTION_CONFIDENCE"] = str(bt)
        cmd = [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            "180",
            "--per-date-direction-json",
            str(per_best.relative_to(ROOT)),
            "--gates-out",
            str(gates_out.relative_to(ROOT)),
            "--summary-out",
            str(summary_out.relative_to(ROOT)),
            "--calibration-note",
            f"frozen30d_best_min_conf={bt}",
        ]
        rc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        gates_block = {
            "exit_code": rc.returncode,
            "gates_json": str(gates_out),
            "summary_json": str(summary_out),
            "combined_all_passed": None,
            "outcome_class": None,
        }
        if gates_out.is_file():
            g = _load(gates_out)
            gates_block["combined_all_passed"] = bool(g.get("combined_all_passed"))
            gates_block["outcome_class"] = g.get("outcome_class")

    report = {
        "schema": "btrack_frozen30d_v1_min_conf_grid_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": "frozen_kpi_a_30d_anchor_dates_btc",
        "anchor_score": str(args.anchor_score),
        "anchor_eval_dates": dates,
        "frozen_kpi_a_baseline_metrics": base_m,
        "grid": grid,
        "candidates": rows,
        "best_by_all_rows_hit_rate": best["min_direction_confidence"] if best else None,
        "best_metrics": best["metrics"] if best else None,
        "best_alert_1_pass_50pct": best.get("alert_1_pass_50pct") if best else False,
        "best_beats_frozen_kpi_a": (
            float((best or {}).get("metrics", {}).get("price_directional_hit_rate") or 0)
            > float(base_m.get("price_directional_hit_rate") or 0)
        )
        if best
        else False,
        "promotion_gates_on_best": gates_block,
        "track_a_auto_promote": False,
        "note": (
            "Per-date v1 rebuilt per min_conf on frozen dates. "
            "combined_all_passed (if run) is 180d walk-forward gates, not 30d headline."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best:
        m = best["metrics"]
        print(
            f"BEST min_conf={best['min_direction_confidence']:.2f} "
            f"all-rows={float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"dir-only={float(m.get('price_hit_rate_on_directional_calls') or 0):.1%} "
            f"calls={m.get('n_directional_calls')} "
            f"A1_50%={'pass' if best.get('alert_1_pass_50pct') else 'fail'}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
