#!/usr/bin/env python3
"""Promote FinOps wire domain v1 L1 closeout after commander approval (B-track, internal)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DRAFT = ROOT / "reports/finops_wire_domain_v1_closeout_draft_latest.json"
EVAL = ROOT / "reports/finops_wire_domain_v1_eval_latest.json"
L3_GRID = ROOT / "reports/finops_wire_l3_restore_grid_v1_latest.json"
DEFAULT_OFFICIAL = ROOT / "docs/final/artifacts/finops_wire_domain_v1_closeout_official_v1_latest.json"
COMMANDER_ACK = ROOT / "docs/final/artifacts/finops_wire_domain_v1_commander_close_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def promote(*, commander_note: str, approved_by: str) -> dict[str, Any]:
    draft = _read(DRAFT)
    ev = _read(EVAL)
    l3 = _read(L3_GRID)

    if not draft:
        return {"ok": False, "error": "closeout_draft_missing", "path": str(DRAFT)}
    if ev.get("ok") is not True:
        return {"ok": False, "error": "domain_eval_not_ok", "path": str(EVAL)}
    gates = ev.get("gates") or {}
    if not all(gates.values()):
        return {"ok": False, "error": "domain_gates_failed", "gates": gates}

    approved_at = _utc()
    official: dict[str, Any] = {
        "ok": True,
        "schema": "finops_wire_domain_v1_closeout_official_v1",
        "generated_at_utc": approved_at,
        "approval_status": "APPROVED_COMMANDER",
        "approved_at_utc": approved_at,
        "approved_by": approved_by,
        "commander_note": commander_note,
        "classification": "INTERNAL_ONLY",
        "domain_id": draft.get("domain_id") or "finops_handoff_v1",
        "lane": "L1_official",
        "parent_rq_019": draft.get("parent_rq_019") or "CLOSED",
        "branch_target": draft.get("branch_target") or "b-track-finops-wire-v1",
        "operator_runbook": draft.get("operator_runbook"),
        "pointers": {
            **(draft.get("pointers") or {}),
            "closeout_draft": DRAFT.relative_to(ROOT).as_posix(),
            "l3_restore_grid": L3_GRID.relative_to(ROOT).as_posix() if l3.get("ok") else None,
        },
        "finops_kpis": draft.get("finops_kpis"),
        "domain_gates": gates,
        "l3_summary": (l3.get("summary") if l3.get("ok") else None),
        "disclaimer_ko": draft.get("disclaimer_ko"),
        "boundary_ack": (
            "L1 official closeout for FinOps wire v1 (B-track). "
            "Not Track A, live trading, L2 commercial, or external send without legal."
        ),
        "remaining_human_gates": [
            "legal_before_external_send",
            "optional_pilot_customer_corpus",
        ],
        "research_only": True,
        "forbidden_claims": [
            "lossless",
            "100_percent_restore",
            "lingua_franca_complete",
            "track_a_auto_promotion",
            "ai_language_fully_complete",
        ],
    }

    commander_close = {
        "schema": "finops_wire_domain_v1_commander_close_v1",
        "generated_at_utc": approved_at,
        "classification": "INTERNAL_ONLY",
        "domain_id": official["domain_id"],
        "lane": "L1_official",
        "parent_rq_019": "CLOSED",
        "approved_by": approved_by,
        "commander_note": commander_note,
        "official_closeout_pointer": DEFAULT_OFFICIAL.relative_to(ROOT).as_posix(),
        "boundary_ack": official["boundary_ack"],
    }

    draft_out = dict(draft)
    draft_out["approval_status"] = "APPROVED_COMMANDER"
    draft_out["approved_at_utc"] = approved_at
    draft_out["approved_by"] = approved_by
    draft_out["official_pointer"] = DEFAULT_OFFICIAL.relative_to(ROOT).as_posix()
    draft_out["human_gates_before_official"] = official["remaining_human_gates"]

    DEFAULT_OFFICIAL.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OFFICIAL.write_text(json.dumps(official, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COMMANDER_ACK.write_text(json.dumps(commander_close, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DRAFT.write_text(json.dumps(draft_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "schema": "finops_wire_domain_v1_promote_result_v1",
        "generated_at_utc": approved_at,
        "official_closeout": DEFAULT_OFFICIAL.relative_to(ROOT).as_posix(),
        "commander_close": COMMANDER_ACK.relative_to(ROOT).as_posix(),
        "draft_updated": DRAFT.relative_to(ROOT).as_posix(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commander-ack", action="store_true", required=True, help="Required: commander approved L1 closeout")
    ap.add_argument("--approved-by", default="commander", help="Approver label for audit trail")
    ap.add_argument("--note", default="commander approved FinOps wire domain v1 L1 closeout", help="Audit note")
    args = ap.parse_args()

    doc = promote(commander_note=args.note, approved_by=args.approved_by)
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
