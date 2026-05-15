#!/usr/bin/env python3
"""Assemble a reproducible B-track prophecy gate evidence pack (internal / Track C prep).

Not a legal or clinical claim pack. Outputs JSON (+ optional MD) listing artifact paths,
gate taxonomy, and one-line reproduction commands. research_only; no A-track promotion.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_gate_evidence_pack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build prophecy gate evidence pack v1")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    art = ROOT / "docs" / "final" / "artifacts"
    reports = ROOT / "reports"
    gates_path = art / "prophecy_promotion_gates_v1_latest.json"
    panel_path = art / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
    hit_path = art / "prophecy_hit_rate_eval_latest.json"
    alerts_path = reports / "prophecy_panel_24h_alerts_latest.json"

    gates = _read_json(gates_path)
    pack: dict[str, Any] = {
        "schema": "prophecy_gate_evidence_pack_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_pointers": {
            "public_facing_checklist": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "track_c_plan": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
            "b2b_draft": "docs/research/TRACK_C_B2B_GUT_BRAIN_METAPHOR_ONEPAGER_DRAFT_V1.md",
        },
        "gate_taxonomy_summary": {
            "outcome_class": gates.get("outcome_class"),
            "promotion_recommendation": gates.get("promotion_recommendation"),
            "combined_all_passed": gates.get("combined_all_passed"),
            "gate_taxonomy": gates.get("gate_taxonomy"),
        },
        "artifacts": {
            "prophecy_promotion_gates_v1_latest": str(gates_path.relative_to(ROOT)).replace("\\", "/"),
            "prophecy_promotion_gates_panel_calibrated": str(panel_path.relative_to(ROOT)).replace("\\", "/"),
            "prophecy_hit_rate_eval_latest": str(hit_path.relative_to(ROOT)).replace("\\", "/"),
            "prophecy_panel_24h_alerts_latest": str(alerts_path.relative_to(ROOT)).replace("\\", "/"),
            "mkm_trackc_ops_dashboard_latest": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
        },
        "artifact_exists": {
            k: Path(ROOT / v).is_file()
            for k, v in {
                "gates": gates_path,
                "panel": panel_path,
                "hit": hit_path,
                "alerts": alerts_path,
            }.items()
        },
        "reproduction_commands": [
            "py scripts/eval_prophecy_promotion_gates_v1.py",
            "py scripts/build_mkm_trackc_ops_dashboard_v1.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Check-ProphecyPanel24hAlerts.ps1",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_btrack_daily_hypothesis_chain.ps1",
        ],
        "disclaimer": (
            "Evidence pack for internal review and Track C narrative prep only. "
            "Not investment advice; not clinical proof; not zero-liability or zero-error claims."
        ),
    }

    text = json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
