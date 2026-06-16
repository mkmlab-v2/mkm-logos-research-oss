#!/usr/bin/env python3
"""[HYPO] Build rib55 human adjudication workflow bundle (Charter step 4).

Prereq smoke + checklist template + passive corral gates.
Does NOT auto-unlock send_gate or ready_for_external_send.
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
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
TEMPLATE = ROOT / "docs/final/artifacts/rib55_overlay_adjudication_record_v1.template.json"
OUT = ROOT / "docs/final/artifacts/rib55_adjudication_workflow_v1_latest.json"
REPORT = ROOT / "reports/rib55_adjudication_workflow_v1_latest.json"

PENDING_STATUSES = frozenset(
    {
        "pending_adjudication",
        "rendered_pending_adjudication",
        "adjudicated_l0_v1_g0_pass",
    }
)
REQUIRED_CHECKLIST_IDS = (
    "base_license_verified",
    "overlay_geometry_plausible",
    "angle_label_theory_not_measurement",
    "no_clinical_diagnosis_claim",
    "l0_l1_ablation_reviewed",
    "education_use_only_scope",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _manifest_has_coord_v2() -> bool:
    if not MANIFEST.is_file():
        return False
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return bool(doc.get("coord_v2") and doc.get("coord_spec_v2"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-prereq-chain", action="store_true")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    exit_code = 0

    if not args.skip_prereq_chain:
        if not _manifest_has_coord_v2():
            steps.append(_run([sys.executable, "scripts/build_rib55_manifest_coord_v2_v1.py"], label="build_coord_v2"))
            if steps[-1]["exit_code"] != 0:
                exit_code = steps[-1]["exit_code"]
        if exit_code == 0:
            steps.append(
                _run([sys.executable, "scripts/validate_anatomy_overlay_coord_v2_v1.py"], label="validate_coord_v2")
            )
            if steps[-1]["exit_code"] != 0:
                exit_code = steps[-1]["exit_code"]
        if exit_code == 0:
            steps.append(
                _run([sys.executable, "scripts/run_rib55_angle_overlay_passive_smoke_v1.py"], label="passive_smoke")
            )
            if steps[-1]["exit_code"] != 0:
                exit_code = steps[-1]["exit_code"]

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    pending = [
        e.get("entry_id")
        for e in manifest.get("entries") or []
        if e.get("status") in PENDING_STATUSES
    ]

    doc = {
        "schema": "rib55_adjudication_workflow_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "charter_step": "LENS_UTILIZATION_CHARTER / anatomy protocol §4 step 4",
        "passive_corral": {
            "send_gate": "HOLD",
            "ready_for_external_send": False,
            "adjudication_auto_unlock_forbidden": True,
            "economic_edge_claim_allowed": False,
        },
        "prereq_steps": steps,
        "prereq_ok": exit_code == 0,
        "pending_entry_ids": pending,
        "artifacts": {
            "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "pilot_png": "docs/final/artifacts/rib55_overlay_pilot_ninth_rib_55deg_v0_latest.png",
            "ablation": "docs/final/artifacts/rib55_l0_l1_ablation_v1_latest.json",
            "coord_v2_validation": "docs/final/artifacts/anatomy_overlay_coord_v2_validation_v1_latest.json",
            "adjudication_template": str(TEMPLATE.relative_to(ROOT)).replace("\\", "/"),
        },
        "human_workflow_ko": [
            "1. pilot PNG·L0/L1 ablation PNG 육안 검수",
            "2. template JSON 복사 → reviewer_display·signed_at_utc·checklist.passed 채움",
            "3. decision을 approved_education_internal | approved_with_reservations | rejected 로 설정",
            "4. py scripts/validate_rib55_overlay_adjudication_v1.py --record-json <PATH>",
            "5. py scripts/apply_rib55_overlay_adjudication_v1.py --record-json <PATH> (검증 통과 후)",
            "6. 외부 송출은 별도 legal/HOLD 해제 — adjudication만으로 send_gate 열리지 않음",
        ],
        "required_checklist_ids": list(REQUIRED_CHECKLIST_IDS),
        "reproduce": {
            "workflow": "py scripts/build_rib55_adjudication_workflow_v1.py",
            "validate_record": "py scripts/validate_rib55_overlay_adjudication_v1.py --record-json <PATH>",
            "apply_record": "py scripts/apply_rib55_overlay_adjudication_v1.py --record-json <PATH>",
        },
        "operator_lines": [
            "- [RIB55-ADJ] human adjudication workflow; send_gate=HOLD.",
            f"- [RIB55-ADJ] pending_entries={pending}",
            f"- [RIB55-ADJ] prereq_ok={exit_code == 0}",
        ],
    }

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")

    print(json.dumps({"ok": exit_code == 0, "out": str(args.out_json), "pending": pending}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
