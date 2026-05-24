#!/usr/bin/env python3
"""COMP-ANCHOR-06b: registry conceptual atoms vs codebook atom_id gap report (no invented mapping)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs/final/artifacts/atom_anchor_registry_v1.json"
SCAN = ROOT / "reports/constitution/btrack_pilot/comp_anchor05_verse_pool_full_scan_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor06_registry_codebook_bridge_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig")) if REGISTRY.is_file() else {}
    scan = json.loads(SCAN.read_text(encoding="utf-8")) if SCAN.is_file() else {}
    registry_rows = scan.get("registry_atoms") or []

    codebook_path = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41775_rows_latest.json"
    lang_counts: dict[str, int] = {}
    if codebook_path.is_file():
        doc = json.loads(codebook_path.read_text(encoding="utf-8"))
        for ent in doc.get("entries") or []:
            if not isinstance(ent, dict):
                continue
            aid = str(ent.get("atom_id") or "")
            lang = aid.split("::", 1)[0] if "::" in aid else "unknown"
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    conceptual = [str(r.get("atom_id")) for r in reg.get("atoms") or [] if isinstance(r, dict)]
    bridge_rows = []
    for cid in conceptual:
        bridge_rows.append(
            {
                "registry_atom_id": cid,
                "in_master_codebook": any(
                    r.get("atom_id") == cid for r in registry_rows if r.get("atom_id") == cid
                ),
                "verses_with_hits": next(
                    (r.get("verses_with_hits") for r in registry_rows if r.get("atom_id") == cid),
                    0,
                ),
                "bridge_status": "unmapped",
                "note": (
                    "English conceptual label; map via seed_symbol_sequences or "
                    "hebrew/greek atom_id overlays — not auto-merged to Track A."
                ),
            }
        )

    report = {
        "schema": "comp_anchor06_registry_codebook_bridge_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "registry_conceptual_count": len(conceptual),
        "codebook_lang_histogram": lang_counts,
        "bridge_rows": bridge_rows,
        "verdict": (
            "Registry conceptual atoms are not lexicon atom_ids; verse hits require "
            "explicit mapping table (future B-track) before Logos anchor queries."
        ),
        "do_not": ["auto_promote_to_track_a", "treat_registry_id_as_codebook_key"],
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "conceptual": len(conceptual)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
