#!/usr/bin/env python3
"""P0+P1+완화 P2 hybrid batch — wiring only; P3 (Track A/live) unchanged.

  py scripts/run_p0_p1_p2_hybrid_batch_v1.py

Outputs: reports/p0_p1_p2_hybrid_batch_v1_latest.json
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
OUT = ROOT / "reports/p0_p1_p2_hybrid_batch_v1_latest.json"
PILOT_PREREQS = ROOT / "reports/btrack_swarm_tier_a_pilot_prereqs_v1_latest.json"
P1_WIRING = ROOT / "reports/p1_advisory_ops_wiring_v1_latest.json"
THREE_LENS = ROOT / "docs/final/artifacts/three_lens_external_intel_snapshot_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> dict[str, Any]:
    print(f"==> [{label}]", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    return {"label": label, "exit_code": rc, "cmd": cmd, "ok": rc == 0}


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_p1_wiring() -> dict[str, Any]:
    shock = _read(ROOT / "docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json")
    brief = _read(ROOT / "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json")
    external = _read(THREE_LENS)
    return {
        "schema": "p1_advisory_ops_wiring_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "excluded_from_final_call": True,
        "gate_mode": "warning",
        "track_a_promotion_approved": False,
        "live_trading_approved": False,
        "wiring": {
            "operator_posture_source": "docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json",
            "morning_brief_source": "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json",
            "external_intel_proxy": str(THREE_LENS.relative_to(ROOT)).replace("\\", "/"),
            "ops_index_hint": "storage/meta/mkm_ops_memory_index_v1.json",
            "resume_pack_hint": "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
        },
        "snapshot": {
            "attach_mode": ((brief or {}).get("field_final_call") or {}).get("attach_mode"),
            "today_action": (brief or {}).get("today_action"),
            "operator_posture": (shock or {}).get("today_evaluation", {}).get("operator_posture"),
            "external_intel_ready": (external or {}).get("ready_for_orchestrator_context"),
        },
        "forbidden": [
            "Final Call auto-merge from sidebar",
            "Track A promotion from advisory wiring",
            "live order keys",
        ],
        "reproduce": "py scripts/run_p0_p1_p2_hybrid_batch_v1.py --skip-p0 --skip-p2",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-p0", action="store_true")
    ap.add_argument("--skip-p1", action="store_true")
    ap.add_argument("--skip-p2", action="store_true")
    ap.add_argument("--pilot-min-krx-weekdays", type=int, default=15)
    ap.add_argument("--skip-three-lens", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_p0:
        for key, script in (
            ("p0_shock_policy", "scripts/build_kospi_shock_conditional_attach_operator_policy_v1.py"),
            ("p0_morning_brief", "scripts/build_internal_kospi_morning_brief_onepager_v1.py"),
            ("p0_logos_passive_drift", "scripts/run_logos_passive_drift_governance_chain_v1.py"),
        ):
            cmd = [py, str(ROOT / script)]
            if key == "p0_logos_passive_drift":
                cmd.append("--fast")
            steps[key] = _run(key, cmd)
            ok = ok and steps[key]["ok"]

    if not args.skip_p1:
        if not args.skip_three_lens:
            steps["p1_three_lens_refresh"] = _run(
                "p1_three_lens_refresh",
                [py, str(ROOT / "scripts/build_three_lens_external_intel_snapshot_v1.py")],
            )
            ok = ok and steps["p1_three_lens_refresh"]["ok"]

        p1 = _build_p1_wiring()
        P1_WIRING.parent.mkdir(parents=True, exist_ok=True)
        P1_WIRING.write_text(json.dumps(p1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps["p1_advisory_wiring"] = {"ok": True, "artifact": str(P1_WIRING)}

    if not args.skip_p2:
        steps["p2_pilot_prereqs"] = _run(
            "p2_pilot_prereqs",
            [
                py,
                str(ROOT / "scripts/check_btrack_swarm_tier_a_prereqs_v1.py"),
                "--min-krx-weekdays",
                str(args.pilot_min_krx_weekdays),
                "--out-json",
                str(PILOT_PREREQS),
            ],
        )
        ok = ok and steps["p2_pilot_prereqs"]["ok"]
        pilot = _read(PILOT_PREREQS) or {}
        pilot_doc = {
            "schema": "btrack_swarm_tier_a_pilot_v1",
            "generated_at_utc": _utc(),
            "gate_mode": "warning",
            "tier": "tier_a_pilot",
            "min_krx_weekday_rows": args.pilot_min_krx_weekdays,
            "production_tier_a_min": 30,
            "track_a_merge_forbidden": True,
            "fusion_pipeline_merge_allowed": False,
            "external_intel_proxy": str(THREE_LENS.relative_to(ROOT)).replace("\\", "/"),
            "prereqs": pilot,
            "note_ko": "15일=pilot 탐색 only · 30일=tier_a production gate · three_lens=병렬 프록시",
        }
        pilot_path = ROOT / "reports/btrack_swarm_tier_a_pilot_v1_latest.json"
        pilot_path.write_text(json.dumps(pilot_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps["p2_pilot_manifest"] = {"ok": True, "artifact": str(pilot_path)}

    doc = {
        "schema": "p0_p1_p2_hybrid_batch_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "gate_mode": "warning",
        "p3_hard_lock": {
            "track_a_promotion_approved": False,
            "live_trading_approved": False,
            "send_gate": "HOLD",
            "final_call_auto_merge": False,
        },
        "packages": {
            "p0_wiring": not args.skip_p0,
            "p1_advisory_non_gating": not args.skip_p1,
            "p2_pilot_tier_a_15": not args.skip_p2,
        },
        "steps": steps,
        "ok": ok,
        "artifacts": {
            "batch_manifest": str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "p1_advisory_wiring": str(P1_WIRING.relative_to(ROOT)).replace("\\", "/"),
            "tier_a_pilot": "reports/btrack_swarm_tier_a_pilot_v1_latest.json",
            "logos_passive_drift": "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json",
            "shock_policy": "docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json",
            "morning_brief": "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json",
        },
        "reproduce": "py scripts/run_p0_p1_p2_hybrid_batch_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
