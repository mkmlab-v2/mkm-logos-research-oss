#!/usr/bin/env python3
"""Post-release-signoff next steps: refresh ops packets, evidence, rollback drill (no auto-live)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_post_release_next_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step: str, cmd: list[str]) -> dict[str, Any]:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    cp = subprocess.run(cmd, cwd=str(ROOT))
    return {"step": step, "exit_code": cp.returncode, "ok": cp.returncode == 0}


def _snap() -> dict[str, Any]:
    art = ROOT / "docs/final/artifacts"
    out: dict[str, Any] = {}
    for name, key in (
        ("prophecy_release_signoff_packet_v1_latest.json", "release_packet"),
        ("prophecy_live_enable_checklist_v1_latest.json", "live_enable_checklist"),
        ("prophecy_manual_live_switch_packet_v1_latest.json", "live_switch_packet"),
        ("prophecy_manual_promotion_decision_lock_v1_latest.json", "manual_lock"),
        ("prophecy_track_a_candidate_v1_latest.json", "candidate"),
    ):
        p = art / name
        if p.is_file():
            o = json.loads(p.read_text(encoding="utf-8"))
            out[key] = {
                "status": o.get("status"),
                "final_decision": o.get("final_decision"),
                "ready_for_release_signoff": (o.get("summary") or {}).get("ready_for_release_signoff"),
                "ready_to_enable_live": (o.get("summary") or {}).get("ready_to_enable_live"),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--apply-candidate-bridge", action="store_true")
    ap.add_argument(
        "--include-promotion-push",
        action="store_true",
        help="Run promotion_push (180d v1 sweep; overwrites strict dual SSOT — default skip).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(_run("release_signoff_packet", [py, "scripts/build_prophecy_release_signoff_packet_v1.py"]))
    steps.append(_run("release_checklist", [py, "scripts/build_prophecy_approved_candidate_release_checklist_v1.py"]))
    steps.append(_run("live_enable_checklist", [py, "scripts/build_prophecy_live_enable_checklist_v1.py"]))
    steps.append(_run("live_rollback_policy", [py, "scripts/build_prophecy_live_rollback_policy_v1.py"]))
    steps.append(_run("live_rollback_drill", [py, "scripts/run_prophecy_live_rollback_drill_v1.py"]))
    steps.append(_run("manual_live_switch_packet", [py, "scripts/build_prophecy_manual_live_switch_packet_v1.py"]))
    steps.append(_run("gate_evidence_pack", [py, "scripts/build_prophecy_gate_evidence_pack_v1.py"]))
    steps.append(_run("v1_human_review_pack", [py, "scripts/build_btrack_v1_price_only_human_review_pack_v1.py"]))
    steps.append(_run("readiness_report", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]))
    steps.append(_run("weekly_pack", [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"]))

    if args.include_promotion_push:
        push_cmd = [py, "scripts/run_btrack_promotion_push_v1.py"]
        if args.apply_candidate_bridge:
            push_cmd.append("--apply-candidate-bridge")
        steps.append(_run("promotion_push", push_cmd))
    else:
        steps.append(
            _run(
                "dual_strict_ssot_touch",
                [
                    py,
                    "scripts/run_btrack_lens_v2_dual_strict_promotion_chain_v1.py",
                    "--skip-directions-rebuild",
                    "--run-promotion-bundle",
                ],
            )
        )

    restore_note = (
        "post-release: commander lock restore after promotion_push (live 별도)."
        if args.include_promotion_push
        else "post-release: strict SSOT preserved (no promotion_push); lock refresh."
    )
    steps.append(
        _run(
            "commander_lock_restore",
            [
                py,
                "scripts/run_btrack_commander_approval_finalize_v1.py",
                "--reviewer",
                args.reviewer,
                "--note",
                restore_note,
            ],
        )
    )
    steps.append(_run("release_signoff_packet_final", [py, "scripts/build_prophecy_release_signoff_packet_v1.py"]))
    steps.append(_run("release_checklist_final", [py, "scripts/build_prophecy_approved_candidate_release_checklist_v1.py"]))

    cp = subprocess.run(
        [py, "scripts/athena_checkpoint.py", "B-track post-release: release READY, live 별도, 30d v1 56.7% research"],
        cwd=str(ROOT),
    )
    steps.append({"step": "athena_checkpoint", "exit_code": cp.returncode, "ok": cp.returncode == 0})

    snap = _snap()
    pack = {
        "schema": "btrack_post_release_next_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "live_trading_auto_enabled": False,
        "steps": steps,
        "governance_snapshot": snap,
        "all_ok": all(s.get("ok") for s in steps),
        "operator_lines": [
            "- [MKM-NEXT] Release signoff READY — Track A candidate bridge 완료.",
            "- [MKM-NEXT] 실매매 ON은 live_enable_event 별도 승인 필요 (이번 체인은 자동 live 미실행).",
            "- [MKM-NEXT] 주간 리뷰: 30d v1 56.7% / frozen 43.3% / hybrid 60% (앵커).",
            "- [MKM-NEXT] strict auto-promote는 streak 0/5 — 연구 레인 병렬은 계속 가능.",
        ],
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"release={snap.get('release_packet', {}).get('status')} live_switch={snap.get('live_switch_packet', {}).get('status')}")
    return 0 if pack["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
