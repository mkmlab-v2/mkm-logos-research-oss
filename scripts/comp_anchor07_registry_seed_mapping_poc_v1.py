#!/usr/bin/env python3
"""COMP-ANCHOR-07: seed_symbol_sequences overlay PoC (explicit HYPO, no Track A merge)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs/final/artifacts/atom_anchor_registry_v1.json"
CODEBOOK = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41775_rows_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor07_registry_seed_mapping_poc_v1.json"

# Manual HYPO anchors: conceptual step -> example codebook atom_id (verified present in lexicon)
HYPO_OVERLAY: dict[str, list[str]] = {
    "BOUNDARY_COMMAND": ["hebrew::לא", "hebrew::אמר"],
    "DESIRE_TRIGGER": ["hebrew::אכל", "hebrew::עץ"],
    "TRANSGRESSION_ACT": ["hebrew::אכל", "hebrew::עץ"],
    "SHAME_AWARENESS": ["hebrew::ירא", "hebrew::עירם"],
    "EXILE_PATTERN": ["hebrew::מצרים", "hebrew::גלה"],
    "RESTORATION_ARC": ["hebrew::יהוה", "hebrew::שוב"],
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _codebook_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(e.get("atom_id"))
        for e in doc.get("entries") or []
        if isinstance(e, dict) and e.get("atom_id")
    }


def main() -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig")) if REGISTRY.is_file() else {}
    known = _codebook_ids(CODEBOOK)
    sequences = reg.get("seed_symbol_sequences") or {}

    seq_rows: list[dict] = []
    for seq_name, steps in sequences.items():
        if not isinstance(steps, list):
            continue
        step_rows = []
        for cid in steps:
            cid = str(cid)
            candidates = HYPO_OVERLAY.get(cid, [])
            verified = [a for a in candidates if a in known]
            step_rows.append(
                {
                    "registry_atom_id": cid,
                    "hypo_codebook_candidates": candidates,
                    "verified_in_codebook": verified,
                    "mapping_status": "hypo_overlay" if verified else "unmapped",
                }
            )
        seq_rows.append({"sequence_id": seq_name, "steps": step_rows})

    report = {
        "schema": "comp_anchor07_registry_seed_mapping_poc_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
        },
        "verdict": (
            "seed_symbol_sequences are narrative overlays; verified hebrew:: atom_ids "
            "are examples only — require human curation before Logos anchor queries."
        ),
        "sequences": seq_rows,
        "do_not": ["auto_merge_to_track_a", "treat_hypo_overlay_as_production_mapping"],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "sequences": len(seq_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
