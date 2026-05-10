#!/usr/bin/env python3
"""Promotion gate: GO vs HOLD from ABC comparison or holdout suite report (exit code)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def _as_abs(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (WORKSPACE_ROOT / path)


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="MKM control-integrity promotion gate")
    ap.add_argument(
        "--comparison",
        default="docs/final/artifacts/model_profile_abc_comparison_latest.json",
        help="ABC comparison artifact (optional if --holdout-only)",
    )
    ap.add_argument(
        "--holdout-report",
        default="",
        help="Optional holdout suite merged report path",
    )
    # Align with build_mkm_control_integrity_model_profile_abc_comparison_v1.py defaults / oracle ceiling on test.
    ap.add_argument("--min-row-pass-rate", type=float, default=0.70)
    ap.add_argument("--min-must-include-rate", type=float, default=0.70)
    ap.add_argument("--min-locked-eval-pass-rate", type=float, default=0.0, help="If >0, require holdout report")
    ap.add_argument(
        "--min-holdout-row-pass-weighted",
        type=float,
        default=0.0,
        help="If >0, require merge report summary.row_pass_rate_weighted >= threshold",
    )
    ap.add_argument("--holdout-only", action="store_true", help="Only check holdout report thresholds")
    ap.add_argument(
        "--report-out",
        default="reports/mkm_control_integrity_promotion_gate_latest.json",
        help="Write gate JSON here (default: reports/mkm_control_integrity_promotion_gate_latest.json)",
    )
    args = ap.parse_args()

    decision = "GO"
    reasons: list[str] = []

    if not args.holdout_only:
        comp_path = _as_abs(args.comparison)
        if not comp_path.is_file():
            print(f"missing comparison: {comp_path}", file=sys.stderr)
            return 1
        comp = _load(comp_path)
        profiles = comp.get("profiles", {})
        min_row = float(args.min_row_pass_rate)
        min_inc = float(args.min_must_include_rate)
        for key, prof in profiles.items():
            if not isinstance(prof, dict):
                continue
            rp = float(prof.get("row_pass_rate", 0.0))
            mi = float(prof.get("must_include_pass_rate", 0.0))
            gp = prof.get("gate_pass")
            if gp is False or rp < min_row or mi < min_inc:
                decision = "HOLD"
                reasons.append(f"{key}: row_pass={rp} must_include={mi} gate_pass={gp}")

    if args.holdout_report or args.min_locked_eval_pass_rate > 0:
        hr_path = _as_abs(args.holdout_report) if args.holdout_report else None
        if not hr_path or not hr_path.is_file():
            if args.min_locked_eval_pass_rate > 0:
                decision = "HOLD"
                reasons.append("holdout report required but missing")
        else:
            hr = _load(hr_path)
            locked = hr.get("by_split", {}).get("locked_eval", {})
            summ = locked.get("summary", {})
            lr = float(summ.get("row_pass_rate", 0.0))
            if args.min_locked_eval_pass_rate > 0 and lr < args.min_locked_eval_pass_rate:
                decision = "HOLD"
                reasons.append(f"locked_eval row_pass_rate={lr} < {args.min_locked_eval_pass_rate}")
            hs = hr.get("summary", {})
            if isinstance(hs, dict):
                wr = float(hs.get("row_pass_rate_weighted", 0.0))
                if args.min_holdout_row_pass_weighted > 0 and wr < args.min_holdout_row_pass_weighted:
                    decision = "HOLD"
                    reasons.append(
                        f"holdout row_pass_rate_weighted={wr} < {args.min_holdout_row_pass_weighted}"
                    )

    out = {
        "schema": "mkm_control_integrity_promotion_gate_v1",
        "decision": decision,
        "reasons": reasons,
        "inputs": {
            "comparison": args.comparison if not args.holdout_only else None,
            "holdout_report": args.holdout_report or None,
        },
        "thresholds": {
            "min_row_pass_rate": args.min_row_pass_rate,
            "min_must_include_rate": args.min_must_include_rate,
            "min_locked_eval_pass_rate": args.min_locked_eval_pass_rate,
            "min_holdout_row_pass_weighted": args.min_holdout_row_pass_weighted,
        },
    }

    report_path = _as_abs(args.report_out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"decision={decision}")
    print(f"report={report_path}")
    if reasons:
        for r in reasons:
            print(f"reason: {r}")
    return 0 if decision == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
