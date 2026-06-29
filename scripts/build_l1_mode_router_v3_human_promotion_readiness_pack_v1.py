#!/usr/bin/env python3
"""Assemble human sign-off readiness pack: L1 v3 ops + wire weekly + Track A gate (no auto-apply)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT_DEFAULT = ROOT / "reports" / "l1_mode_router_v3_human_promotion_readiness_pack_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dry_run_apply() -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "apply_multilens_ultra_compression_track_a_promotion_v1.py"),
        "--human-approve-promotion",
        "--dry-run",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    parsed: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            parsed = {"parse_error": True, "stdout_tail": proc.stdout[-500:]}
    return {"exit_code": proc.returncode, "dry_run": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    active = _load(ART / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json")
    candidate = _load(ART / "MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json")
    signoff = _load(ART / "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json")
    daily = _load(ART / "l1_inverse_decoder_daily_gate_v1_latest.json")
    failure = _load(ART / "l1_inverse_decoder_failure_profile_v1_latest.json")
    canary = _load(ART / "l1_inverse_decoder_mode_router_v3_canary_status_latest.json")
    wire_scope = _load(PILOT / "comp_v2_wire_staging_promotion_scope_v1.json")
    wire_summary = _load(PILOT / "comp_v2_wire_shadow_metering_summary_v1.json")

    env = candidate.get("promotion_candidate_envelope") or {}
    gates = env.get("selected_promotion_gates") or {}
    active_variant = (active.get("active_profile") or {}).get("promoted_variant_id") or signoff.get(
        "selected_variant_id"
    )
    candidate_variant = env.get("selected_variant_id")
    active_saving = (active.get("compression_metrics") or {}).get("global_token_saving_rate")
    candidate_saving = (env.get("selected_metrics") or {}).get("global_token_saving_rate")

    would_change_active = not (
        active_variant == candidate_variant
        and active_saving == candidate_saving
        and bool(gates.get("auto_track_a_promotion_allowed"))
    )

    dry = _dry_run_apply()
    wire_pytest_ok = bool((wire_scope.get("pytest_wire_bundle") or {}).get("passed"))
    daily_ok = bool((daily.get("gate") or {}).get("all_ok"))
    canary_ok = (canary.get("decision") or {}).get("action") == "KEEP_CANARY"

    pack = {
        "schema": "l1_mode_router_v3_human_promotion_readiness_pack_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": {
            "l1_mode_router_v3_auto_track_a_merge": False,
            "wire_shadow_auto_active_write": False,
            "live_trading_auto_promotion": False,
        },
        "commander_signoff_required_for": [
            "apply_multilens_ultra_compression_track_a_promotion_v1.py --human-approve-promotion (no --dry-run)",
        ],
        "track_a_frozen_headline": {
            "global_token_saving_rate": active_saving,
            "avg_jaccard": (active.get("compression_metrics") or {}).get("avg_reconstruction_fidelity_jaccard"),
            "active_variant_id": active_variant,
            "active_report": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "last_signoff_utc": signoff.get("approved_at_utc"),
        },
        "promotion_candidate": {
            "variant_id": candidate_variant,
            "gates": gates,
            "would_change_active": would_change_active,
            "apply_dry_run_exit_code": dry.get("exit_code"),
            "apply_dry_run_ok": dry.get("exit_code") == 0,
        },
        "l1_mode_router_v3_ops": {
            "decoder_path": (daily.get("inputs") or {}).get("decoder_path"),
            "daily_gate_decision": (daily.get("gate") or {}).get("decision"),
            "daily_gate_all_ok": daily_ok,
            "swap_typo_exact": (daily.get("results") or {}).get("swap_typo", {}).get("avg_exact_restore_rate"),
            "failure_profile_swap_typo_exact": failure.get("aggregate", {}).get("avg_exact_restore_rate"),
            "order_only_ratio": (failure.get("failure_types") or [{}])[0].get("ratio") if failure.get("failure_types") else None,
            "canary_phase": canary.get("phase"),
            "canary_action": (canary.get("decision") or {}).get("action"),
            "canary_ok": canary_ok,
        },
        "wire_shadow_weekly": {
            "pytest_exit": (wire_scope.get("pytest_wire_bundle") or {}).get("exit_code"),
            "pytest_passed": wire_pytest_ok,
            "case_pairs": wire_summary.get("case_pairs"),
            "scope_generated_at_utc": wire_scope.get("generated_at_utc"),
        },
        "readiness": {
            "wire_weekly_green": wire_pytest_ok,
            "l1_daily_gate_green": daily_ok,
            "l1_canary_keep": canary_ok,
            "track_a_apply_dry_run_green": dry.get("exit_code") == 0,
            "human_apply_recommended_now": would_change_active and dry.get("exit_code") == 0,
            "status_label": (
                "READY_HUMAN_APPLY_TRACK_A_DELTA"
                if would_change_active and dry.get("exit_code") == 0
                else "OPS_GREEN_NO_TRACK_A_DELTA"
            ),
        },
        "apply_command_template": (
            "py scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py "
            "--human-approve-promotion --reviewer commander --note \"<한줄>\""
        ),
        "rollback_l1_v3": "User env L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1",
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "status_label": pack["readiness"]["status_label"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
