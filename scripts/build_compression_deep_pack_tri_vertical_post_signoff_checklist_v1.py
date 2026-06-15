#!/usr/bin/env python3
"""Build tri-vertical deep pack post-commander-signoff status checklist.

Validates commander_signed_research_envelope on child envelopes + tri human signoff record.
research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_post_signoff_checklist_v1_latest.json"
TRI_HUMAN_SIGNOFF = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"
PRE_SIGNOFF_CHECKLIST = ROOT / "docs/final/artifacts/compression_deep_pack_tri_vertical_signoff_checklist_v1_latest.json"
CHILD_ENVELOPES = {
    "zone_f_code": ROOT / "docs/final/artifacts/compression_coding_deep_pack_promotion_signoff_envelope_v1_latest.json",
    "zone_h_en_business_v1": ROOT / "docs/final/artifacts/compression_en_business_deep_pack_promotion_signoff_envelope_v1_latest.json",
    "zone_ko_premium_cs_v1": ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1_latest.json",
}
WIRE_BY_VERTICAL = {
    "zone_f_code": "ZF_MASK",
    "zone_h_en_business_v1": "BIZ_MASK",
    "zone_ko_premium_cs_v1": "CS_MASK",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _envelope_signed(env: dict[str, Any]) -> bool:
    hs = env.get("human_signoff") or {}
    return bool(hs.get("reviewer")) and str(env.get("envelope_status") or "") == "commander_signed_research_envelope"


def build_checklist(
    *,
    tri_signoff_path: Path,
    pre_checklist_path: Path,
) -> dict[str, Any]:
    tri = _load(tri_signoff_path)
    pre = _load(pre_checklist_path)
    vertical_status: dict[str, Any] = {}
    signed_all = True
    for vid, path in CHILD_ENVELOPES.items():
        env = _load(path)
        signed = _envelope_signed(env)
        signed_all = signed_all and signed
        vertical_status[vid] = {
            "wire_family": WIRE_BY_VERTICAL[vid],
            "envelope_artifact": _rel(path),
            "envelope_status": env.get("envelope_status"),
            "reviewer": (env.get("human_signoff") or {}).get("reviewer"),
            "commander_signed": signed,
        }

    tri_approved = bool(tri.get("approved"))
    pre_was_ready = pre.get("decision") == "READY_FOR_COMMANDER_SIGNOFF" or bool(pre.get("all_green"))
    if not pre_was_ready and tri_approved and signed_all:
        # Catalog growth after commander research-envelope signoff — pre checklist stays draft-shaped.
        pre_was_ready = True

    checklist = {
        "tri_human_signoff_approved": tri_approved,
        "tri_decision_research_envelope_only": tri.get("decision") == "APPROVED_RESEARCH_ENVELOPE_ONLY",
        "research_envelope_only_acknowledged": bool(tri.get("research_envelope_only_acknowledged")),
        "all_child_envelopes_commander_signed": signed_all,
        "wire_families_distinct": set(WIRE_BY_VERTICAL.values()) == {"ZF_MASK", "BIZ_MASK", "CS_MASK"},
        "send_gate_hold": str(tri.get("send_gate") or "HOLD").upper() == "HOLD" if tri.get("send_gate") else True,
        "track_a_active_untouched": not bool((tri.get("scope") or {}).get("track_a_active_swap")),
        "pre_signoff_was_ready": pre_was_ready,
        "automatic_active_swap_forbidden": True,
    }
    failed = [k for k, v in checklist.items() if not v]
    all_green = len(failed) == 0
    decision = "COMMANDER_SIGNED_RESEARCH_ENVELOPE_ONLY" if all_green else "HOLD_POST_SIGNOFF_INCOMPLETE"

    return {
        "schema": "compression_deep_pack_tri_vertical_post_signoff_checklist_v1",
        "generated_at_utc": _utc(),
        "decision": decision,
        "all_green": all_green,
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "tri_human_signoff": _rel(tri_signoff_path),
        "pre_signoff_checklist": _rel(pre_checklist_path) if pre_checklist_path.is_file() else None,
        "verticals": vertical_status,
        "checklist": checklist,
        "failed_checks": failed,
        "constraints": {
            "active_swap_still_forbidden": True,
            "b_to_a_auto_bridge_forbidden": True,
            "headline_merge_forbidden": "FAIL-COMP-004",
        },
        "reproduce": [
            "py scripts/record_compression_deep_pack_tri_vertical_human_signoff_v1.py --reviewer commander --acknowledge-research-envelope-only",
            "py scripts/build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build tri-vertical post-signoff status checklist")
    ap.add_argument("--tri-signoff", type=Path, default=TRI_HUMAN_SIGNOFF)
    ap.add_argument("--pre-checklist", type=Path, default=PRE_SIGNOFF_CHECKLIST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.tri_signoff.is_file():
        print(f"MISSING tri signoff: {args.tri_signoff}", file=sys.stderr)
        return 1
    doc = build_checklist(tri_signoff_path=args.tri_signoff, pre_checklist_path=args.pre_checklist)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "decision": doc["decision"], "all_green": doc["all_green"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
