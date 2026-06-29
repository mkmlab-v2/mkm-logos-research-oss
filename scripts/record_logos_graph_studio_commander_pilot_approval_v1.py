#!/usr/bin/env python3
"""Record commander approval for Logos Graph Studio internal B2B pilot (not external SEND)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json"
SIGNOFF_TEMPLATE = ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"
COMMERCIAL_READINESS = ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json"
APPROVAL_LOG = ROOT / "reports/logos_graph_studio_commander_pilot_approval_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def apply(*, commander_ack: bool, counsel_ack: bool, note: str) -> dict[str, Any]:
    external_ok = commander_ack and counsel_ack
    doc: dict[str, Any] = {
        "schema": "logos_graph_studio_commander_pilot_approval_v1",
        "generated_at_utc": _utc(),
        "commander_signoff": commander_ack,
        "counsel_signoff": counsel_ack,
        "decision": "ACK_INTERNAL_B2B_PILOT" if commander_ack else "HOLD",
        "send_gate": "OPEN" if external_ok else "HOLD",
        "ready_for_external_send": external_ok,
        "ready_for_internal_b2b_pilot": commander_ack,
        "ready_for_billing_implementation": False,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
        },
        "approved_artifacts": [
            "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md",
            "docs/final/artifacts/logos_graph_studio_pilot_sow_template_v1_latest.md",
            "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md",
            "docs/final/artifacts/logos_graph_studio_b2b_live_rehearsal_checklist_v1_latest.md",
            "docs/final/artifacts/logos_graph_studio_pilot_sow_executive_summary_v1_latest.md",
        ],
        "demo_primary_url": (
            "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
            "?preset=job_job_suffering_reason"
        ),
        "commercial_workspace_url": "https://logos.jema-ai.com/logos-research",
        "evidence_pointers": {
            "l9_l12": "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json",
            "b2b_rehearsal_live": "reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json",
            "public_smoke": "reports/showroom_trust_viz_public_chain_smoke_latest.json",
        },
        "note": note,
        "boundary_ack": (
            "Commander approval enables internal B2B pilot meetings and SOW negotiation only. "
            "External SEND, billing, and ready_for_external_send require separate legal counsel sign-off."
        ),
    }

    OUT_DEFAULT.parent.mkdir(parents=True, exist_ok=True)
    OUT_DEFAULT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if SIGNOFF_TEMPLATE.is_file():
        signoff = _load(SIGNOFF_TEMPLATE)
        if commander_ack:
            signoff["commander_signoff"] = {
                "present": True,
                "reviewer_id": "commander",
                "signoff_utc": doc["generated_at_utc"],
                "decision": "ACK_INTERNAL_B2B_PILOT_GRAPH_STUDIO",
                "notes": note,
            }
        signoff["ready_for_external_send"] = False
        SIGNOFF_TEMPLATE.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readiness = _load(COMMERCIAL_READINESS)
    if readiness:
        readiness["generated_at_utc"] = doc["generated_at_utc"]
        readiness["commander_pilot_approval"] = OUT_DEFAULT.relative_to(ROOT).as_posix()
        readiness["ready_for_internal_b2b_pilot"] = commander_ack
        readiness["ready_for_external_send"] = external_ok
        if not counsel_ack:
            readiness["ready_for_external_send_note"] = (
                "Commander pilot ack recorded; counsel_signoff false — external send HOLD."
            )
        COMMERCIAL_READINESS.write_text(json.dumps(readiness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_row = {
        "generated_at_utc": doc["generated_at_utc"],
        "commander_signoff": commander_ack,
        "counsel_signoff": counsel_ack,
        "send_gate": doc["send_gate"],
        "decision": doc["decision"],
        "artifact": str(OUT_DEFAULT.resolve()),
    }
    APPROVAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with APPROVAL_LOG.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(log_row, ensure_ascii=False) + "\n")

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commander-acknowledge", action="store_true")
    ap.add_argument("--counsel-acknowledge", action="store_true")
    ap.add_argument(
        "--note",
        default="Commander chat approval 2026-06-20: internal B2B Graph Studio pilot GO; external send HOLD.",
    )
    args = ap.parse_args()
    if not args.commander_acknowledge and not args.counsel_acknowledge:
        print(json.dumps({"ok": False, "error": "pass --commander-acknowledge and/or --counsel-acknowledge"}))
        return 1
    doc = apply(
        commander_ack=args.commander_acknowledge,
        counsel_ack=args.counsel_acknowledge,
        note=args.note,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT_DEFAULT),
                "send_gate": doc["send_gate"],
                "ready_for_external_send": doc["ready_for_external_send"],
                "ready_for_internal_b2b_pilot": doc["ready_for_internal_b2b_pilot"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
