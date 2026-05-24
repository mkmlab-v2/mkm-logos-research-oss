#!/usr/bin/env python3
"""COMP-ANCHOR-08: human curation queue from seed mapping PoC (no auto-promote)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING = ROOT / "reports/constitution/btrack_pilot/comp_anchor07_registry_seed_mapping_poc_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor08_seed_curation_queue_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not MAPPING.is_file():
        print(f"missing {MAPPING}", file=sys.stderr)
        return 1

    doc = json.loads(MAPPING.read_text(encoding="utf-8"))
    queue: list[dict] = []
    for seq in doc.get("sequences") or []:
        seq_id = str(seq.get("sequence_id") or "")
        for step in seq.get("steps") or []:
            queue.append(
                {
                    "queue_id": f"{seq_id}::{step.get('registry_atom_id')}",
                    "sequence_id": seq_id,
                    "registry_atom_id": step.get("registry_atom_id"),
                    "hypo_codebook_candidates": step.get("hypo_codebook_candidates"),
                    "verified_in_codebook": step.get("verified_in_codebook"),
                    "human_status": "pending",
                    "approved_codebook_atom_id": None,
                    "reviewer_note": "",
                }
            )

    report = {
        "schema": "comp_anchor08_seed_curation_queue_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "pending_count": sum(1 for q in queue if q["human_status"] == "pending"),
        "queue": queue,
        "instructions": [
            "Set human_status to approved|rejected and approved_codebook_atom_id when curated.",
            "Do not auto-merge queue into Track A or live trading.",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "items": len(queue)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
