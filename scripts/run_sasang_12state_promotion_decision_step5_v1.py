#!/usr/bin/env python3
"""Step-5: conservative promotion decision for veto-only vs hold."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
IN_STEP3 = ART / "sasang_12state_walkforward_step3_latest.json"
IN_STEP4 = ART / "sasang_12state_baseline_comparison_step4_latest.json"
OUT = ART / "sasang_12state_promotion_decision_step5_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_lane_summary(step3: dict[str, Any], lane: str) -> dict[str, Any]:
    for x in step3.get("lane_results", []):
        if isinstance(x, dict) and x.get("lane") == lane and isinstance(x.get("summary"), dict):
            return x["summary"]
    return {}


def _safe_lane_summary4(step4: dict[str, Any], lane: str) -> dict[str, Any]:
    for x in step4.get("lane_results", []):
        if isinstance(x, dict) and x.get("lane") == lane and isinstance(x.get("summary"), dict):
            return x["summary"]
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step3-json", type=Path, default=IN_STEP3)
    ap.add_argument("--step4-json", type=Path, default=IN_STEP4)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.step3_json.is_file() or not args.step4_json.is_file():
        raise SystemExit("missing step3/step4 artifact")
    step3 = json.loads(args.step3_json.read_text(encoding="utf-8"))
    step4 = json.loads(args.step4_json.read_text(encoding="utf-8"))

    eq3 = _safe_lane_summary(step3, "equity_30y")
    cr3 = _safe_lane_summary(step3, "crypto_5y")
    eq4 = _safe_lane_summary4(step4, "equity_30y")
    cr4 = _safe_lane_summary4(step4, "crypto_5y")

    eq_mdd = float(eq3.get("mdd_improved_ratio", 0.0))
    eq_cvar = float(eq3.get("cvar_improved_ratio", 0.0))
    cr_mdd = float(cr3.get("mdd_improved_ratio", 0.0))
    cr_cvar = float(cr3.get("cvar_improved_ratio", 0.0))
    eq_sig = bool(eq4.get("mdd_significant_lt_0_05")) and bool(eq4.get("cvar_significant_lt_0_05"))
    cr_sig = bool(cr4.get("mdd_significant_lt_0_05")) and bool(cr4.get("cvar_significant_lt_0_05"))

    protective_pass = (eq_mdd >= 0.7 and eq_cvar >= 0.7 and cr_mdd >= 0.5 and cr_cvar >= 0.5 and (eq_sig or cr_sig))
    directional_pass = False  # explicitly disabled in this stage

    if protective_pass and not directional_pass:
        decision = "GATING_VETO_ONLY_CANDIDATE"
        next_step = "Prepare human approval for veto-only activation; keep directional auto-bridge forbidden."
    elif protective_pass and directional_pass:
        decision = "A_TRACK_PROMOTION_CANDIDATE_READY"
        next_step = "Prepare full human approval packet for controlled Track A bridge."
    else:
        decision = "HOLD"
        next_step = "Keep NON_GATING; extend experiments and improve robustness."

    out = {
        "schema": "sasang_12state_promotion_decision_step5_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "step3": str(args.step3_json).replace("\\", "/"),
            "step4": str(args.step4_json).replace("\\", "/"),
        },
        "checks": {
            "equity_mdd_ratio": eq_mdd,
            "equity_cvar_ratio": eq_cvar,
            "crypto_mdd_ratio": cr_mdd,
            "crypto_cvar_ratio": cr_cvar,
            "equity_significance_pass": eq_sig,
            "crypto_significance_pass": cr_sig,
            "protective_pass": protective_pass,
            "directional_pass": directional_pass,
        },
        "decision": decision,
        "gating_scope": "veto_only_non_directional" if decision.startswith("GATING_VETO_ONLY") else "hold_no_promotion",
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "next_step": next_step,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
