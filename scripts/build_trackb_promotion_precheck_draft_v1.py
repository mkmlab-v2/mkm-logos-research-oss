#!/usr/bin/env python3
"""Rebuild docs/final/artifacts/trackb_promotion_precheck_draft_latest.json from on-disk Track B artifacts.

Quality gates are read from JSON; runtime timings are optional CLI inputs (measure separately).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "trackb_promotion_precheck_draft_latest.json"

DEFAULT_ROBUST = (
    "docs/final/artifacts/trackb_quaternion_generalization_v6_round3_exact_guarded_robust_latest.json"
)
DEFAULT_SPLIT_A = "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_a_latest.json"
DEFAULT_SPLIT_B1 = "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b1_latest.json"
DEFAULT_SPLIT_B2 = "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_exact_robust_split_b2_latest.json"
DEFAULT_WEEKLY = "docs/final/artifacts/trackb_weekly_gate_recheck_latest.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _min_exact_stress(doc: dict[str, Any]) -> float | None:
    rows = doc.get("rows") or []
    if not rows or not isinstance(rows[0], dict):
        return None
    ss = rows[0].get("stress_summary") or {}
    v = ss.get("min_exact_sequence_match_rate_over_grid")
    return float(v) if v is not None else None


def _robust_short_rate(doc: dict[str, Any]) -> tuple[float | None, bool]:
    best = doc.get("best") if isinstance(doc.get("best"), dict) else {}
    ms = best.get("min_short_bucket_rate")
    rate = float(ms) if ms is not None else None
    tp = bool(doc.get("target_passed", False))
    return rate, tp


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track B promotion precheck draft JSON.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--robust", type=Path, default=ROOT / DEFAULT_ROBUST)
    ap.add_argument("--split-a", type=Path, default=ROOT / DEFAULT_SPLIT_A)
    ap.add_argument("--split-b1", type=Path, default=ROOT / DEFAULT_SPLIT_B1)
    ap.add_argument("--split-b2", type=Path, default=ROOT / DEFAULT_SPLIT_B2)
    ap.add_argument("--weekly-gate", type=Path, default=ROOT / DEFAULT_WEEKLY)
    ap.add_argument("--runtime-budget-ms", type=int, default=300_000)
    ap.add_argument("--weekly-refresh-ms", type=int, default=None, help="Wall ms for Run-TrackBWeeklyRefresh.ps1")
    ap.add_argument("--split-a-ms", type=int, default=None)
    ap.add_argument("--split-b-ms", type=int, default=None, help="split_b1 extended elapsed")
    ap.add_argument("--split-b2-ms", type=int, default=None)
    ap.add_argument(
        "--weekly-exit-code",
        type=int,
        default=None,
        help="Last weekly refresh exit code if known (0 = ok)",
    )
    ap.add_argument(
        "--weekly-b2-included",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether weekly included extended B2",
    )
    args = ap.parse_args()

    gates = {
        "exact_short_bucket_min": 0.95,
        "stress_exact_floor": 0.75,
        "weekly_gate_decision_required": "GO_RESEARCH",
        "operational_runtime_budget_ms": int(args.runtime_budget_ms),
    }

    robust_path = args.robust
    split_a_path = args.split_a
    split_b1_path = args.split_b1
    split_b2_path = args.split_b2
    weekly_path = args.weekly_gate

    missing = [p for p in (robust_path, split_a_path, split_b1_path, split_b2_path, weekly_path) if not p.is_file()]
    if missing:
        print("ERROR: missing inputs:", file=__import__("sys").stderr)
        for m in missing:
            print(f"  {m}", file=__import__("sys").stderr)
        return 2

    rdoc = _read(robust_path)
    sa = _read(split_a_path)
    sb1 = _read(split_b1_path)
    sb2 = _read(split_b2_path)
    wdoc = _read(weekly_path)

    short_rate, target_passed = _robust_short_rate(rdoc)
    min_a = _min_exact_stress(sa)
    min_b1 = _min_exact_stress(sb1)
    min_b2 = _min_exact_stress(sb2)
    weekly_decision = str(wdoc.get("decision") or "")

    robust_ok = (
        short_rate is not None
        and short_rate >= gates["exact_short_bucket_min"]
        and target_passed
    )
    stress_ok = all(
        x is not None and x >= gates["stress_exact_floor"]
        for x in (min_a, min_b1, min_b2)
    )
    weekly_ok = weekly_decision == gates["weekly_gate_decision_required"]

    runtime_obs: dict[str, Any] = {
        "split_a_elapsed_ms": args.split_a_ms,
        "split_b_elapsed_ms": args.split_b_ms,
        "weekly_refresh_wall_ms": args.weekly_refresh_ms,
        "split_b2_standalone_elapsed_ms": args.split_b2_ms,
    }
    times_known = any(v is not None for v in runtime_obs.values())
    weekly_ms = args.weekly_refresh_ms
    if times_known and weekly_ms is not None:
        runtime_budget_ok = weekly_ms <= gates["operational_runtime_budget_ms"]
    elif not times_known:
        runtime_budget_ok = None
    else:
        runtime_budget_ok = weekly_ms <= gates["operational_runtime_budget_ms"]

    extended_chain_stability_ok = bool(weekly_ok and (args.weekly_exit_code in (None, 0)))

    checks: dict[str, Any] = {
        "robust_target_passed": bool(robust_ok),
        "robust_min_short_bucket_rate": short_rate,
        "stress_split_a_min_exact": min_a,
        "stress_split_b1_min_exact": min_b1,
        "stress_split_b2_min_exact": min_b2,
        "weekly_gate_decision": weekly_decision,
        "runtime_observation_ms": runtime_obs,
        "runtime_budget_ok": runtime_budget_ok,
        "extended_chain_stability_ok": extended_chain_stability_ok,
        "weekly_refresh_verified": {
            "script": "scripts/Run-TrackBWeeklyRefresh.ps1",
            "flags": [
                "IncludeExtendedStressGrid",
                "SkipSsmSmoke",
                "SkipCosine",
            ],
            "exit_code": args.weekly_exit_code,
            "elapsed_ms": weekly_ms,
            "extended_b2_included": bool(args.weekly_b2_included),
            "note": (
                "Timings optional: pass --weekly-refresh-ms etc. after measured runs. "
                "Length-64 B2 often run standalone via run_trackb_top_combo_stress_grid.py."
            ),
        },
    }

    quality_ok = robust_ok and stress_ok and weekly_ok
    if quality_ok and runtime_budget_ok is True:
        decision = "HOLD_PROMOTION_PRECHECK_DRAFT"
        reason = (
            "Quality gates pass for research lane; runtime within reference budget — promotion to "
            "Track A remains blocked by SSOT §9 and human gate; update scope explicitly if claiming production."
        )
    elif quality_ok and runtime_budget_ok is False:
        decision = "HOLD_PROMOTION_PRECHECK_DRAFT"
        reason = (
            "Research lane quality OK; weekly refresh wall time exceeds operational_runtime_budget_ms; "
            "production promotion out of scope."
        )
    elif quality_ok and runtime_budget_ok is None:
        decision = "HOLD_PROMOTION_PRECHECK_DRAFT"
        reason = (
            "Research lane quality OK; runtime timings not supplied — set --weekly-refresh-ms (and split timings) "
            "after measured runs to evaluate runtime_budget_ok."
        )
    else:
        decision = "HOLD_PROMOTION_PRECHECK_DRAFT"
        reason = (
            f"Quality or weekly gate incomplete: robust_ok={robust_ok}, stress_ok={stress_ok}, "
            f"weekly_ok={weekly_ok} (decision={weekly_decision!r})."
        )

    out: dict[str, Any] = {
        "schema": "trackb_promotion_precheck_draft_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate_artifact": str(DEFAULT_ROBUST).replace("\\", "/"),
        "artifact_inputs": {
            "robust": str(robust_path.relative_to(ROOT)).replace("\\", "/"),
            "split_a": str(split_a_path.relative_to(ROOT)).replace("\\", "/"),
            "split_b1": str(split_b1_path.relative_to(ROOT)).replace("\\", "/"),
            "split_b2": str(split_b2_path.relative_to(ROOT)).replace("\\", "/"),
            "weekly_gate": str(weekly_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "gates": gates,
        "checks": checks,
        "decision": decision,
        "decision_reason": reason,
        "next_actions": [
            "If total runtime must drop: lower --samples-per-cell-cap on split steps or narrow OOV grid.",
            "Re-run build_trackb_promotion_precheck_draft_v1.py with measured --weekly-refresh-ms after weekly refresh.",
        ],
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"decision={decision} quality_ok={quality_ok} runtime_budget_ok={runtime_budget_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
