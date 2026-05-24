#!/usr/bin/env python3
"""B-track headline gate sweep (min_confidence + score_abs_deadzone) after score panel exists.

Runs sweep_prophecy_headline_deadzone_hold_v1.py with allowlist gate. Does not overwrite
prophecy_hit_rate_eval_latest.json (human_signoff_required). research_only / [HYPO].
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep_prophecy_headline_deadzone_hold_v1.py"
ENSEMBLE = ROOT / "scripts" / "build_btrack_ensemble_per_date_directions_v1.py"
DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_SWEEP_OUT = ROOT / "reports" / "prophecy_headline_deadzone_hold_sweep_v1_latest.json"
DEFAULT_CHAIN_OUT = ROOT / "reports" / "prophecy_btrack_headline_gates_recommended_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _ensure_per_date(*, score_json: Path, per_date_json: Path, recent_trading_days: int) -> int:
    if per_date_json.is_file():
        return 0
    per_date_json.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ENSEMBLE),
        "--recent-trading-days",
        str(max(1, int(recent_trading_days))),
        "--ensemble-mode",
        "v1",
        "--output",
        str(per_date_json),
    ]
    return _run(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument(
        "--min-confidence-grid",
        type=str,
        default="0.0,0.15,0.18,0.22,0.25,0.30",
    )
    ap.add_argument(
        "--score-abs-deadzone-grid",
        type=str,
        default="0.0,0.05,0.10,0.12,0.15,0.18",
    )
    ap.add_argument("--min-coverage-active", type=float, default=0.55)
    ap.add_argument("--sweep-output", type=Path, default=DEFAULT_SWEEP_OUT)
    ap.add_argument("--chain-summary", type=Path, default=DEFAULT_CHAIN_OUT)
    ap.add_argument("--skip-ensemble-build", action="store_true")
    args = ap.parse_args()

    if not args.score_json.is_file():
        print(f"Missing score json: {args.score_json}", file=sys.stderr)
        return 2

    if not args.skip_ensemble_build:
        rc = _ensure_per_date(
            score_json=args.score_json,
            per_date_json=args.per_date_json,
            recent_trading_days=args.recent_trading_days,
        )
        if rc != 0:
            return rc

    if not args.per_date_json.is_file():
        print(f"Missing per-date json: {args.per_date_json}", file=sys.stderr)
        return 2

    sweep_cmd = [
        sys.executable,
        str(SWEEP),
        "--score-json",
        str(args.score_json),
        "--per-date-json",
        str(args.per_date_json),
        "--min-confidence-grid",
        args.min_confidence_grid,
        "--score-abs-deadzone-grid",
        args.score_abs_deadzone_grid,
        "--min-coverage-active",
        str(float(args.min_coverage_active)),
        "--output",
        str(args.sweep_output),
    ]
    rc = _run(sweep_cmd)
    if rc != 0:
        return rc

    sweep_doc = _load_json(args.sweep_output) or {}
    best_pass = sweep_doc.get("best_passing_50_and_coverage")
    best_any = sweep_doc.get("best_by_active_hit_rate")
    chosen = best_pass if isinstance(best_pass, dict) else best_any

    summary: dict[str, Any] = {
        "schema": "prophecy_btrack_headline_gates_recommended_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json.resolve()),
            "per_date_json": str(args.per_date_json.resolve()),
            "min_confidence_grid": args.min_confidence_grid,
            "score_abs_deadzone_grid": args.score_abs_deadzone_grid,
            "sweep_output": str(args.sweep_output.resolve()),
        },
        "sweep_exit_code": 0,
        "recommended_params": (chosen or {}).get("params") if isinstance(chosen, dict) else None,
        "recommended_metrics": (chosen or {}).get("metrics") if isinstance(chosen, dict) else None,
        "headline_kpi_auto_apply": False,
        "human_signoff_required_for": [
            "promote_op28_headline_kpi_v1",
            "prophecy_hit_rate_eval_latest.json",
        ],
        "note": "Sweep only; does not call promote_op28_headline_kpi_v1.",
    }
    args.chain_summary.parent.mkdir(parents=True, exist_ok=True)
    args.chain_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.chain_summary.resolve()}")
    if summary.get("recommended_params"):
        print(f"RECOMMENDED_PARAMS={summary['recommended_params']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
