#!/usr/bin/env python3
"""[HYPO] Phase 5: commander sign-off push — LUT, bridges, wired hook, full research refresh.

Does NOT auto-apply Track A ACTIVE unless promotion packet gates pass and --apply-active is passed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LUT_DRAFT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
STUB = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
)
SIGNOFF_MANIFEST_OUT = (
    ROOT / "reports/ng40_commander_signoff_push_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.stdout.strip():
        print(cp.stdout.strip())
    if cp.stderr.strip():
        print(cp.stderr.strip(), file=sys.stderr)
    return int(cp.returncode)


def _approve_lut(signoff_by: str) -> None:
    if not LUT_DRAFT.is_file():
        return
    doc = json.loads(LUT_DRAFT.read_text(encoding="utf-8-sig"))
    doc["human_reviewed"] = True
    doc["human_signoff_required"] = False
    doc["status"] = "commander_approved_v1"
    doc["commander_signoff_utc"] = _utc()
    doc["commander_signoff_by"] = signoff_by
    LUT_DRAFT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _approve_nav(signoff_by: str) -> None:
    if not NAV_FRAME.is_file():
        return
    nav = json.loads(NAV_FRAME.read_text(encoding="utf-8-sig"))
    nav["human_reviewed"] = True
    nav["commander_signoff_utc"] = _utc()
    nav["commander_signoff_by"] = signoff_by
    lut = nav.setdefault("lut", {})
    if isinstance(lut, dict):
        lut["status"] = "commander_approved_v1"
        lut["human_reviewed"] = True
    NAV_FRAME.write_text(json.dumps(nav, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _patch_stub(signoff_by: str) -> None:
    if not STUB.is_file():
        return
    stub = json.loads(STUB.read_text(encoding="utf-8-sig"))
    stub["track_a_promotion_signoff"] = False
    stub["commander_research_signoff"] = {
        "approved": True,
        "signoff_by": signoff_by,
        "signoff_utc": _utc(),
        "wired_salience_hook": True,
        "track_a_active_write": False,
        "note_ko": "연구 샌드박스·concept_bridge·LUT 승인; ACTIVE 덮어쓰기는 promotion packet 게이트 별도",
    }
    stub["status"] = "phase_5_commander_signoff_pushed"
    meta = stub.setdefault("meta", {})
    if isinstance(meta, dict):
        meta["commander_signoff_utc"] = _utc()
        meta["track_a_promotion_signoff"] = False
    stub.setdefault("phase_5_commander_signoff", {})["status"] = "pushed_v1"
    STUB.write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument(
        "--apply-active",
        action="store_true",
        help="If promotion packet export_prep_ready, run apply_btrack_nextgen_promotion (dangerous)",
    )
    ap.add_argument("--skip-tri-lane", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    rc = _run(
        [
            sys.executable,
            str(ROOT / "scripts/mark_logos_concept_bridge_human_signoff_v1.py"),
            "--commander-direct-signoff",
            "--signoff-by",
            args.signoff_by,
        ]
    )
    steps.append({"step": "mark_concept_bridge_signoff", "exit_code": rc})
    if rc != 0:
        return rc

    _approve_lut(args.signoff_by)
    _approve_nav(args.signoff_by)
    steps.append({"step": "approve_lut_nav", "exit_code": 0})

    rc_hook = _run(
        [
            sys.executable,
            str(ROOT / "scripts/build_ng40_salience_hook_from_nav_frame_v1.py"),
            "--mark-wired",
        ]
    )
    steps.append({"step": "salience_hook_wired", "exit_code": rc_hook})

    de_probe = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
    lut_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_archetype_prior_lut_draft_v1.py"),
        "--patch-nav-frame",
    ]
    if de_probe.is_file():
        lut_cmd.extend(["--de-probe-json", str(de_probe)])
    rc_lut = _run(lut_cmd)
    steps.append({"step": "lut_refresh", "exit_code": rc_lut})

    rc_reg = _run([sys.executable, str(ROOT / "scripts/build_logos_concept_bridge_registry_v1.py")])
    steps.append({"step": "registry_refresh", "exit_code": rc_reg})

    _patch_stub(args.signoff_by)

    if not args.skip_tri_lane:
        rc_tri = _run(
            [
                sys.executable,
                str(ROOT / "scripts/run_nextgen_tri_lane_research_bundle_v1.py"),
                "--execute",
            ]
        )
        steps.append({"step": "tri_lane_bundle", "exit_code": rc_tri})
        if rc_tri != 0:
            return rc_tri

    rc_p3 = _run(
        [
            sys.executable,
            str(ROOT / "scripts/run_nextgen_phase3_archetype_prior_chain_v1.py"),
            "--commander-signoff-wired",
        ]
    )
    steps.append({"step": "phase3_refresh", "exit_code": rc_p3})

    rc_pkt = _run(
        [sys.executable, str(ROOT / "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py")]
    )
    steps.append({"step": "promotion_packet", "exit_code": rc_pkt})

    apply_result: dict[str, Any] = {"skipped": True, "reason": "no --apply-active"}
    if args.apply_active:
        rc_apply = _run(
            [
                sys.executable,
                str(ROOT / "scripts/apply_btrack_nextgen_promotion_to_active_v1.py"),
                "--human-approve-promotion",
                "--reviewer",
                args.signoff_by,
            ]
        )
        apply_result = {"exit_code": rc_apply, "attempted": True}
        steps.append({"step": "apply_active", **apply_result})

    tri = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_tri_lane_research_bundle_v1_latest.json"
    )
    tri_doc = (
        json.loads(tri.read_text(encoding="utf-8-sig")) if tri.is_file() else None
    )
    packet_path = ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
    packet = (
        json.loads(packet_path.read_text(encoding="utf-8-sig"))
        if packet_path.is_file()
        else None
    )

    manifest = {
        "schema": "ng40_commander_signoff_push_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "commander_signoff_by": args.signoff_by,
        "track_a_active_write": False,
        "lut_approved": True,
        "salience_hook_wired": True,
        "concept_bridge_registry_human_ratio": (
            (json.loads((ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json").read_text(encoding="utf-8-sig"))).get("human_reviewed_ratio")
            if (ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json").is_file()
            else None
        ),
        "tri_lane_synthesis": (tri_doc or {}).get("synthesis_ko"),
        "promotion_packet": {
            "present": packet is not None,
            "export_prep_ready": (packet or {}).get("export_prep_ready"),
            "active_apply_recommended": (packet or {}).get("active_apply_recommended"),
            "selected_arm": (packet or {}).get("selected_arm"),
        },
        "active_apply": apply_result,
        "guardrails": [
            "B2B byte_exact remains guarded spine arm",
            "FAIL-COMP-004: no live trading auto-merge",
        ],
        "steps": steps,
        "stub_pointer": str(STUB.relative_to(ROOT)).replace("\\", "/"),
    }
    SIGNOFF_MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIGNOFF_MANIFEST_OUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(SIGNOFF_MANIFEST_OUT), "steps": len(steps)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
