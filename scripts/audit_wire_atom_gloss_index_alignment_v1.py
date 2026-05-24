#!/usr/bin/env python3
"""Audit wire atom_id → lexicon gloss index alignment (B-track COMP-ATOM-05 follow-up)."""

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

DEFAULT_LEX = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_OUT = ROOT / "reports/wire_atom_gloss_index_alignment_v1_latest.json"
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
ANCHOR07 = ROOT / "reports/constitution/btrack_pilot/comp_anchor07_wire_atom_candidates_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_atom_index(lexicon: Path) -> set[str]:
    from scripts.core.master_codebook_lexicon_v1_bridge import _load_atom_id_to_form

    idx = _load_atom_id_to_form(str(lexicon.resolve()))
    return set(idx.keys())


def _collect_wire_atom_ids() -> list[str]:
    from scripts.mkm_graph_wire_bridge_influence_v1 import wire_atom_ids_merged

    return wire_atom_ids_merged(anchor_max=32)


def main() -> int:
    ap = argparse.ArgumentParser(description="Wire atom gloss index alignment audit")
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEX)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.lexicon.is_file():
        print(f"error: missing lexicon {args.lexicon}", file=sys.stderr)
        return 2

    lex_ids = _load_atom_index(args.lexicon)
    wire_ids = _collect_wire_atom_ids()
    known = [aid for aid in wire_ids if aid in lex_ids]
    unknown = [aid for aid in wire_ids if aid not in lex_ids]

  # graph:: prefix atoms are synthetic — expected unknown in lexicon
    graph_pref = [aid for aid in unknown if str(aid).startswith("graph::")]
    hard_unknown = [aid for aid in unknown if not str(aid).startswith("graph::")]

    match_ratio = len(known) / max(1, len(wire_ids))
    doc: dict[str, Any] = {
        "schema": "wire_atom_gloss_index_alignment_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "lexicon_path": str(args.lexicon.relative_to(ROOT)).replace("\\", "/"),
        "wire_atom_id_count": len(wire_ids),
        "known_in_lexicon_count": len(known),
        "unknown_count": len(unknown),
        "hard_unknown_count": len(hard_unknown),
        "graph_synthetic_unknown_count": len(graph_pref),
        "match_ratio": round(match_ratio, 4),
        "known_sample": known[:16],
        "hard_unknown_sample": hard_unknown[:16],
        "proceed_gloss_decompress": len(hard_unknown) == 0 and len(known) >= 3,
        "remediation": (
            "Use wire_atom_ids_merged() ids present in master_codebook_lexicon_v1 entries; "
            "rebuild comp_anchor07 / POC path from lexicon atom_id SSOT."
            if hard_unknown
            else "ok"
        ),
        "sources": {
            "poc": str(POC.relative_to(ROOT)).replace("\\", "/") if POC.is_file() else None,
            "anchor07": str(ANCHOR07.relative_to(ROOT)).replace("\\", "/") if ANCHOR07.is_file() else None,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "match_ratio": doc["match_ratio"]}, ensure_ascii=False))
    return 0 if doc["proceed_gloss_decompress"] or match_ratio >= 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
