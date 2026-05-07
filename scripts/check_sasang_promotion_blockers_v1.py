from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Sasang promotion blockers for A-track readiness.")
    ap.add_argument("--holdout-json", type=Path, default=REPORTS / "agct_sasang_holdout_eval_v1_latest.json")
    ap.add_argument("--gowatch-json", type=Path, default=REPORTS / "agct_sasang_go_watch_pack_v1_latest.json")
    ap.add_argument(
        "--thirty-year-json",
        type=Path,
        default=ART / "prophecy_lens_combo_backtest_30y_latest.json",
    )
    ap.add_argument("--min-holdout-n", type=int, default=10)
    ap.add_argument("--max-review-required", type=int, default=0)
    ap.add_argument("--allow-alt-long-horizon-waiver", action="store_true")
    ap.add_argument("--alt-min-available-years", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=REPORTS / "agct_sasang_promotion_blockers_v1_latest.json")
    args = ap.parse_args()

    holdout = _load_json(args.holdout_json)
    gowatch = _load_json(args.gowatch_json)
    long30 = _load_json(args.thirty_year_json)

    holdout_n = int(((holdout.get("split") or {}).get("holdout_n") or 0))
    runs = gowatch.get("runs") or []
    review_required = sum(1 for r in runs if isinstance(r, dict) and str(r.get("decision") or "") == "REVIEW_REQUIRED")
    thirty_gate = long30.get("thirty_year_claim_gate") or {}
    coverage = long30.get("coverage") or {}
    thirty_ok = bool(thirty_gate.get("allow_30y_generalization"))
    thirty_status = str(((long30.get("thirty_year_claim_gate") or {}).get("status") or "UNKNOWN"))
    available_years = float(coverage.get("available_years") or 0.0)
    waiver_used = False

    blockers: list[dict[str, Any]] = []
    if holdout_n < int(args.min_holdout_n):
        blockers.append(
            {
                "id": "holdout_sample_too_small",
                "severity": "high",
                "observed": holdout_n,
                "required_min": int(args.min_holdout_n),
            }
        )
    if review_required > int(args.max_review_required):
        blockers.append(
            {
                "id": "btrack_variability_review_required_present",
                "severity": "medium",
                "observed": review_required,
                "required_max": int(args.max_review_required),
            }
        )
    if not thirty_ok:
        if bool(args.allow_alt_long_horizon_waiver) and available_years >= float(args.alt_min_available_years):
            waiver_used = True
        else:
            blockers.append(
                {
                    "id": "thirty_year_generalization_not_proven",
                    "severity": "high",
                    "observed_status": thirty_status,
                    "required": "PROVEN_30Y_SCOPE",
                }
            )

    payload = {
        "schema": "agct_sasang_promotion_blockers_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "holdout_json": str(args.holdout_json),
            "gowatch_json": str(args.gowatch_json),
            "thirty_year_json": str(args.thirty_year_json),
            "min_holdout_n": int(args.min_holdout_n),
            "max_review_required": int(args.max_review_required),
            "allow_alt_long_horizon_waiver": bool(args.allow_alt_long_horizon_waiver),
            "alt_min_available_years": float(args.alt_min_available_years),
        },
        "observations": {
            "holdout_n": holdout_n,
            "review_required_runs": review_required,
            "thirty_year_status": thirty_status,
            "available_years": available_years,
        },
        "waivers": {
            "long_horizon_substitute_used": waiver_used,
            "policy": (
                "allow substitute long-horizon pass when strict 30y is structurally unavailable "
                f"and available_years >= {float(args.alt_min_available_years)}"
            ),
        },
        "blockers": blockers,
        "decision": {
            "status": "READY_FOR_MANUAL_SIGNOFF" if not blockers else "HOLD_BLOCKERS_PRESENT",
            "blocker_count": len(blockers),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(f"STATUS={payload['decision']['status']} blockers={len(blockers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
