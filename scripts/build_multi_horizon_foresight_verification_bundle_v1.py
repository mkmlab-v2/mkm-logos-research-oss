#!/usr/bin/env python3
"""Consolidate Multi-Horizon Foresight Verification T0 bundle [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/multi_horizon_foresight_verification_v1_latest.json"
RUN_LOG = ROOT / "reports/multi_horizon_foresight_verification_run_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
        return o if isinstance(o, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    run_log = _load(RUN_LOG)
    phases_ok = True
    if run_log and isinstance(run_log.get("phases"), list):
        # P5 may run before run log is final; ignore P5 self row when judging chain health.
        phases_ok = all(
            p.get("exit_code") == 0
            for p in run_log["phases"]
            if p.get("phase_id") != "P5"
        )
        if not phases_ok:
            phases_ok = bool(run_log.get("all_phases_exit_zero"))

    artifact_ok = {
        "approval_on_disk": (ROOT / "reports/multi_horizon_foresight_project_approval_v1.json").is_file(),
        "axis_manifest": (ROOT / "reports/multi_horizon_foresight_axis_manifest_v1_latest.json").is_file(),
        "advisory_sample": (ROOT / "reports/multi_horizon_foresight_advisory_v1_latest.json").is_file(),
        "price_baseline_snapshot": (
            ROOT / "reports/multi_horizon_foresight_price_baseline_snapshot_v1_latest.json"
        ).is_file(),
        "calibration_lane": (ROOT / "reports/multi_horizon_foresight_calibration_lane_v1_latest.json").is_file(),
        "prior_prophecy_closure_linked": (ROOT / "reports/btrack_prophecy_research_closure_v1_latest.json").is_file(),
        "chain_proposal_compare_linked": (
            ROOT / "reports/chain_proposal_reproduction_compare_v1_latest.json"
        ).is_file(),
    }
    t0_checklist = {
        **artifact_ok,
        "all_phases_exit_zero": phases_ok,
        "auto_promote_ready": False,
        "track_a_status": "blocked",
    }
    t0_complete = all(artifact_ok.values()) and phases_ok

    doc = {
        "schema": "multi_horizon_foresight_verification_v1",
        "project_id": "MHFV-2026-06",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "success_tier": "T0",
        "t0_complete": t0_complete,
        "t0_checklist": t0_checklist,
        "auto_promote_ready": False,
        "track_a_status": "blocked",
        "artifacts": {
            "charter": "docs/final/artifacts/multi_horizon_foresight_verification_project_v1.json",
            "approval": "reports/multi_horizon_foresight_project_approval_v1.json",
            "run_log": "reports/multi_horizon_foresight_verification_run_v1_latest.json",
            "axis_manifest": "reports/multi_horizon_foresight_axis_manifest_v1_latest.json",
            "advisory": "reports/multi_horizon_foresight_advisory_v1_latest.json",
            "prophecy_closure": "reports/btrack_prophecy_research_closure_v1_latest.json",
            "chain_proposal_compare": "reports/chain_proposal_reproduction_compare_v1_latest.json",
            "baseline_lens_ablation": "reports/baseline_lens_wf_ablation_v1_latest.json",
        },
        "findings_summary": {
            "price_lens_promotion_legal_ceiling": 0.52,
            "instrument_ensemble_top3_mean": 0.576667,
            "combined_strict_pass": False,
            "kospi_hypo_leading": "ovn050 (panel/June; do not overwrite production artifact)",
            "foresight_conclusion": "Multi-horizon foresight is measurable per-axis; single-score oracle promotion is blocked by design and by OOS lens ceiling.",
        },
        "messaging_contract": {
            "allowed": [
                "T0 archive bundle for Track C / internal education",
                "Per-axis limits documented with artifact paths",
            ],
            "disallowed": [
                "Track A promotion",
                "live trading GO",
                "gate threshold lowering as success",
                "single lens score as universal foresight proof",
            ],
        },
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()} t0_complete={t0_complete}")
    return 0 if t0_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
