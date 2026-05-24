#!/usr/bin/env python3
"""Commander approval: B-track → Track A **candidate bridge** (not live trading).

Requires prior v1_price_only prod apply + Phase3 aux approval (warn if missing).
Does NOT enable live orders or auto_bridge without separate trading approval.
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
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"
DEFAULT_SIGNOFF = ART / "btrack_track_a_candidate_human_signoff_v1_latest.json"
DEFAULT_HR = REPORTS / "btrack_v1_price_only_human_review_pack_v1_latest.json"
DEFAULT_PROD_APPLY = REPORTS / "btrack_v1_price_only_prod_apply_v1_latest.json"
DEFAULT_PHASE3_APPROVAL = ART / "btrack_phase3_human_approval_v1_latest.json"
DEFAULT_CANDIDATE = ART / "prophecy_track_a_candidate_v1_latest.json"
DEFAULT_GATES = REPORTS / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
DEFAULT_SCORE = ART / "btrack_prophecy_score_latest.json"
DEFAULT_HIT_EVAL = ART / "prophecy_hit_rate_eval_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    cp = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)


def _patch_hr(hr_path: Path, signoff_ref: str, reviewer: str, note: str) -> None:
    hr = _load(hr_path)
    if not hr:
        return
    d = hr.setdefault("decision", {})
    if not isinstance(d, dict):
        return
    d["track_a_promotion"] = True
    d["track_a_scope"] = "candidate_bridge_only"
    d["live_trading_enabled"] = False
    d["human_commander_override"] = "APPROVED_TRACK_A_CANDIDATE_BRIDGE"
    d["human_decision"] = "APPROVED_TRACK_A_CANDIDATE_NOT_LIVE"
    d["human_approved_at_utc"] = _now()
    d["human_reviewer"] = reviewer
    d["human_note_ko"] = note
    hr["track_a_signoff_ref"] = signoff_ref
    hr_path.write_text(json.dumps(hr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PATCHED: {hr_path.resolve()}")


def _refresh_candidate(
    *,
    out: Path,
    gates: dict[str, Any],
    prod_apply: dict[str, Any],
    phase3: dict[str, Any],
    hit_eval: dict[str, Any],
    reviewer: str,
    note: str,
    signoff_ref: str,
) -> None:
    m = hit_eval.get("metrics") if isinstance(hit_eval.get("metrics"), dict) else {}
    post_hit = m.get("price_directional_hit_rate")
    doc = {
        "schema": "prophecy_track_a_candidate_v1",
        "generated_at_utc": _now(),
        "status": "APPROVED_CANDIDATE",
        "source_track": "B",
        "promotion_mode": "human_approved_candidate_only",
        "human_approval": {
            "approved_at_utc": _now(),
            "approval_channel": "cursor_in_chat",
            "reviewer": reviewer,
            "commander_override_formal_gates": True,
            "note": note,
            "signoff_ref": signoff_ref,
        },
        "btrack_stack": {
            "ensemble_profile": "v1_price_only",
            "prod_score_json": str(DEFAULT_SCORE.relative_to(ROOT)).replace("\\", "/"),
            "prod_apply_report": str(DEFAULT_PROD_APPLY.relative_to(ROOT)).replace("\\", "/")
            if prod_apply
            else None,
            "phase3_aux_approved": phase3.get("decision") == "APPROVED",
            "phase3_approval_ref": str(DEFAULT_PHASE3_APPROVAL.relative_to(ROOT)).replace("\\", "/"),
            "post_apply_30d_hit_rate": post_hit,
            "shield_as_direction_gate": "RETIRED",
        },
        "candidate_gate": {
            "promotion_track_mode": gates.get("inputs", {}).get("promotion_track_mode")
            if isinstance(gates.get("inputs"), dict)
            else None,
            "formal_combined_all_passed": gates.get("combined_all_passed"),
            "formal_strict_passed": gates.get("strict_passed"),
            "human_override": True,
        },
        "candidate_metrics": {
            "price_directional_hit_rate_30d_btc": post_hit,
            "n_evaluated_30d_btc": m.get("n_evaluated"),
        },
        "runtime_constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "requires_human_review_each_release": True,
            "live_trading_enabled_by_this_artifact": False,
        },
        "evidence": {
            "promotion_gates_recommended_chain": str(DEFAULT_GATES.relative_to(ROOT)).replace("\\", "/"),
            "prod_apply_report": str(DEFAULT_PROD_APPLY.relative_to(ROOT)).replace("\\", "/"),
            "phase3_human_approval": str(DEFAULT_PHASE3_APPROVAL.relative_to(ROOT)).replace("\\", "/"),
            "hit_rate_eval": str(DEFAULT_HIT_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "insight_sidecar": "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json",
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default=(
            "지휘관 승인: B-track v1_price_only+Phase3 → Track A 후보 브리지. "
            "formal gates 미통과 시 commander override. 실매매·auto_bridge 별도."
        ),
    )
    ap.add_argument("--signoff-out", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--skip-prophecy-chain-scripts", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prod_apply = _load(DEFAULT_PROD_APPLY)
    phase3 = _load(DEFAULT_PHASE3_APPROVAL)
    if not prod_apply and not args.dry_run:
        print("WARN: prod apply report missing; v1_price_only prod may not be applied", file=sys.stderr)
    if phase3.get("decision") != "APPROVED" and not args.dry_run:
        print("WARN: Phase3 human approval artifact not APPROVED", file=sys.stderr)

    signoff_ref = str(args.signoff_out.relative_to(ROOT)).replace("\\", "/")
    gates = _load(DEFAULT_GATES)
    hit_eval = _load(DEFAULT_HIT_EVAL)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "formal_combined_all_passed": gates.get("combined_all_passed"),
                    "post_hit": (hit_eval.get("metrics") or {}).get("price_directional_hit_rate"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    signoff = {
        "schema": "btrack_track_a_candidate_human_signoff_v1",
        "recorded_at_utc": _now(),
        "reviewer": args.reviewer,
        "decision": "APPROVED",
        "scope": {
            "track_a_candidate_bridge": True,
            "live_trading": False,
            "auto_bridge": False,
            "commander_override_formal_gates": True,
        },
        "note": args.note,
        "evidence": {
            "prod_apply": str(DEFAULT_PROD_APPLY),
            "phase3_approval": str(DEFAULT_PHASE3_APPROVAL),
            "promotion_gates": str(DEFAULT_GATES),
            "score_json": str(DEFAULT_SCORE),
        },
        "formal_gate_snapshot": {
            "combined_all_passed": gates.get("combined_all_passed"),
            "promotion_recommendation": gates.get("promotion_recommendation"),
            "outcome_class": gates.get("outcome_class"),
        },
    }
    args.signoff_out.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_out.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.signoff_out.resolve()}")

    _refresh_candidate(
        out=DEFAULT_CANDIDATE,
        gates=gates,
        prod_apply=prod_apply,
        phase3=phase3,
        hit_eval=hit_eval,
        reviewer=args.reviewer,
        note=args.note,
        signoff_ref=signoff_ref,
    )

    _patch_hr(DEFAULT_HR, signoff_ref, args.reviewer, args.note)

    p3 = _load(DEFAULT_PHASE3_APPROVAL)
    if p3:
        scope = p3.setdefault("scope", {})
        if isinstance(scope, dict):
            scope["track_a_candidate_bridge"] = True
        p3["track_a_candidate_signoff_ref"] = signoff_ref
        DEFAULT_PHASE3_APPROVAL.write_text(
            json.dumps(p3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"PATCHED: {DEFAULT_PHASE3_APPROVAL.resolve()}")

    py = sys.executable
    if not args.skip_prophecy_chain_scripts:
        for script in (
            "scripts/record_prophecy_release_human_signoff_v1.py",
            "scripts/lock_prophecy_manual_promotion_decision_v1.py",
            "scripts/build_prophecy_approved_candidate_release_checklist_v1.py",
            "scripts/build_prophecy_release_signoff_packet_v1.py",
            "scripts/refresh_gut_brain_btrack_promotion_status_v1.py",
        ):
            sp = ROOT / script
            if sp.is_file():
                _run([py, str(sp)])

    ld = ROOT / "scripts/log_agent_decision.py"
    if ld.is_file():
        subprocess.run(
            [
                py,
                str(ld),
                "--mission-id",
                "btrack_track_a_candidate",
                "--stage",
                "human_approved",
                "--decision",
                "APPROVED_TRACK_A_CANDIDATE_BRIDGE",
                "--evidence-path",
                str(args.signoff_out.resolve()),
                "--actor",
                args.reviewer,
                "--note",
                args.note[:200],
            ],
            cwd=str(ROOT),
            check=False,
        )

    print("OK Track A candidate bridge approved (live trading / auto_bridge still OFF)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
