#!/usr/bin/env python3
"""Write dual-lane prophecy promotion gates SSOT pointer manifest."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_promotion_gates_ssot_v1 import (  # noqa: E402
    DAILY_SHADOW,
    LEGACY_V1,
    RECOMMENDED_CHAIN,
    REL_DAILY_SHADOW,
    REL_LEGACY_V1,
    REL_RECOMMENDED_CHAIN,
    REL_RUNTIME_HEALTH,
    REL_SSOT_POINTER,
    RUNTIME_HEALTH,
    SSOT_POINTER,
)

SCHEMA = "prophecy_promotion_gates_ssot_pointer_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gate_lane(
    path: Path,
    *,
    rel_path: str,
    lane_id: str,
    role: str,
    writers: list[str],
    readers_note: str,
    ops_closure_primary: bool = False,
) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "lane_id": lane_id,
        "role": role,
        "relative_path": rel_path,
        "path": str(path),
        "exists": path.is_file(),
        "writers": writers,
        "readers_note": readers_note,
        "ops_closure_primary": ops_closure_primary,
    }
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            snap["generated_at_utc"] = doc.get("generated_at_utc")
            snap["promotion_track_mode"] = (doc.get("inputs") or {}).get("promotion_track_mode")
            snap["combined_all_passed"] = doc.get("combined_all_passed")
            snap["auto_promote_ready"] = doc.get("auto_promote_ready")
            snap["outcome_class"] = doc.get("outcome_class")
            tracks = doc.get("tracks") if isinstance(doc.get("tracks"), dict) else {}
            lens = tracks.get("per_date_lens") if isinstance(tracks.get("per_date_lens"), dict) else {}
            for gate in lens.get("gates") or []:
                if isinstance(gate, dict) and gate.get("gate_id") == "lens_wf_mean_test_accuracy":
                    observed = gate.get("observed") if isinstance(gate.get("observed"), dict) else {}
                    snap["lens_wf_mean_test_accuracy"] = observed.get("mean_test_accuracy")
                    break
        except (json.JSONDecodeError, OSError):
            snap["parse_error"] = True
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=SSOT_POINTER)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    health_snap: dict[str, Any] = {
        "relative_path": REL_RUNTIME_HEALTH,
        "path": str(RUNTIME_HEALTH),
        "exists": RUNTIME_HEALTH.is_file(),
        "default_gates_reader": "scripts/evaluate_prophecy_runtime_health_v1.py (--gates-json)",
        "recommended_gates_json": REL_DAILY_SHADOW,
    }
    if RUNTIME_HEALTH.is_file():
        try:
            doc = json.loads(RUNTIME_HEALTH.read_text(encoding="utf-8"))
            health_snap["generated_at_utc"] = doc.get("generated_at_utc")
            health_snap["status"] = doc.get("status")
            inputs = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
            health_snap["gates_json_used"] = inputs.get("gates_json")
            summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
            health_snap["auto_promote_ready"] = summary.get("auto_promote_ready")
        except (json.JSONDecodeError, OSError):
            health_snap["parse_error"] = True

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "policy": {
            "ops_closure_promotion_hold": REL_DAILY_SHADOW,
            "runtime_health_default_gates": REL_DAILY_SHADOW,
            "legacy_v1_latest_warning": (
                "prophecy_promotion_gates_v1_latest.json may be stale or recommended-chain dual-lane; "
                "do not use alone for B-track auto-promote HOLD."
            ),
            "track_a_live_auto_merge": False,
        },
        "lanes": {
            "daily_shadow": _gate_lane(
                DAILY_SHADOW,
                rel_path=REL_DAILY_SHADOW,
                lane_id="daily_shadow_btrack",
                role="daily_btrack_chain_strict_promotion",
                writers=[
                    "scripts/run_btrack_daily_hypothesis_chain.ps1 (eval_prophecy_promotion_gates_v1.py)",
                ],
                readers_note=(
                    "Primary for ops closure / prophecy HOLD. btc_only_crossassist + v1_latest walkforward inputs."
                ),
                ops_closure_primary=True,
            ),
            "legacy_v1_latest": _gate_lane(
                LEGACY_V1,
                rel_path=REL_LEGACY_V1,
                lane_id="legacy_v1_latest",
                role="legacy_default_output_stale_risk",
                writers=["scripts/eval_prophecy_promotion_gates_v1.py (default --output)"],
                readers_note=(
                    "May lag daily chain; often dual + recommended_chain walkforward. "
                    "Health guard previously defaulted here — prefer daily_shadow."
                ),
                ops_closure_primary=False,
            ),
            "recommended_chain": _gate_lane(
                RECOMMENDED_CHAIN,
                rel_path=REL_RECOMMENDED_CHAIN,
                lane_id="recommended_eval_chain",
                role="recommended_sweep_lane",
                writers=["scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"],
                readers_note="Research sweep lane; not daily ops closure SSOT.",
                ops_closure_primary=False,
            ),
        },
        "runtime_health_guard": health_snap,
        "relative_paths": {
            "daily_shadow": REL_DAILY_SHADOW,
            "legacy_v1_latest": REL_LEGACY_V1,
            "recommended_chain": REL_RECOMMENDED_CHAIN,
            "ssot_pointer": REL_SSOT_POINTER,
            "runtime_health": REL_RUNTIME_HEALTH,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
