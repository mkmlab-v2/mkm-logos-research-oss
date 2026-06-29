#!/usr/bin/env python3
"""Apply curated-learning human-gate ack for encounter_sequence disagreements [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply(*, human_gate_ack: bool = False, dummy_auto_fill: bool = False) -> dict[str, Any]:
    if not (human_gate_ack or dummy_auto_fill):
        return {
            "schema": "encounter_sequence_curated_learning_apply_v1",
            "applied": False,
            "reason": "human_gate_ack_required",
        }
    drafts_doc = json.loads(DRAFTS.read_text(encoding="utf-8-sig")) if DRAFTS.is_file() else {}
    drafts = drafts_doc.get("drafts") if isinstance(drafts_doc.get("drafts"), list) else []
    if not drafts and not dummy_auto_fill:
        return {"schema": "encounter_sequence_curated_learning_apply_v1", "applied": False, "reason": "no_drafts"}

    ack_doc = {
        "schema": "encounter_sequence_curated_learning_human_gate_ack_v1",
        "generated_at_utc": _utc(),
        "human_gate_ack": True,
        "dummy_autofill": bool(dummy_auto_fill),
        "research_only": True,
        "draft_count": len(drafts),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "track_a_bridge": False,
        "sequence_ids": [d.get("sequence_id") for d in drafts if isinstance(d, dict)],
        "note_ko": (
            "[DUMMY] B-track autofill ack; auto-training·Track A 금지"
            if dummy_auto_fill
            else "human-gate ack recorded; auto-training·Track A 금지"
        ),
    }
    ACK.parent.mkdir(parents=True, exist_ok=True)
    ACK.write_text(json.dumps(ack_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    if drafts:
        with REGISTRY.open("a", encoding="utf-8") as f:
            for d in drafts:
                if not isinstance(d, dict):
                    continue
                row = {
                    "schema": "encounter_sequence_curated_learning_registry_row_v1",
                    "recorded_at_utc": _utc(),
                    "sequence_id": d.get("sequence_id"),
                    "disagreement_code": d.get("disagreement_code"),
                    "curated_path_status": "pending_human_review",
                    "human_gate_ack": True,
                    "dummy_autofill": bool(dummy_auto_fill),
                    "note_ko": ack_doc["note_ko"],
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "schema": "encounter_sequence_curated_learning_apply_v1",
        "applied": True,
        "dummy_autofill": bool(dummy_auto_fill),
        "draft_count": len(drafts),
        "ack_path": str(ACK).replace("\\", "/"),
        "registry_path": str(REGISTRY).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-gate-ack", action="store_true")
    ap.add_argument(
        "--dummy-auto-fill",
        action="store_true",
        help="B-track dummy autofill ack (research_only; not physician sign-off)",
    )
    args = ap.parse_args()
    doc = apply(human_gate_ack=args.human_gate_ack, dummy_auto_fill=args.dummy_auto_fill)
    print(json.dumps(doc, ensure_ascii=False))
    if doc.get("reason") == "human_gate_ack_required":
        return 2
    return 0 if doc.get("applied") else 1


if __name__ == "__main__":
    raise SystemExit(main())
