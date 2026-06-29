#!/usr/bin/env python3
"""Build bidirectional 41k<->31k anchor index (verse->atoms and atom->verses)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSE_ATOM_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_with_atoms_latest.jsonl"
OUT_DEFAULT = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(*, max_atom_per_verse: int, max_verse_per_atom: int) -> dict[str, Any]:
    verse_to_atoms: dict[str, list[dict[str, Any]]] = {}
    atom_to_verses: dict[str, list[dict[str, Any]]] = {}
    if not VERSE_ATOM_JSONL.is_file():
        return {"schema": "logos_bidirectional_anchor_index_v1", "ok": False, "error": "missing verse atom jsonl"}
    with VERSE_ATOM_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            top_atoms = (((row.get("atom_overlay") or {}).get("top_atoms")) or [])[:max_atom_per_verse]
            if not vid or not top_atoms:
                continue
            verse_to_atoms[vid] = [
                {
                    "atom_id": a.get("atom_id"),
                    "normalized_form": a.get("normalized_form"),
                    "weight": a.get("weight"),
                }
                for a in top_atoms
            ]
            for a in top_atoms:
                aid = str(a.get("atom_id") or "")
                if not aid:
                    continue
                atom_to_verses.setdefault(aid, []).append({"verse_id": vid, "weight": a.get("weight")})
    for aid in list(atom_to_verses.keys()):
        rows = sorted(atom_to_verses[aid], key=lambda r: float(r.get("weight") or 0), reverse=True)[:max_verse_per_atom]
        atom_to_verses[aid] = rows
    return {
        "schema": "logos_bidirectional_anchor_index_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {"track_a_bridge": False, "live_trading_bridge": False},
        "inputs": {
            "verse_atom_jsonl": str(VERSE_ATOM_JSONL.relative_to(ROOT)).replace("\\", "/"),
            "max_atom_per_verse": max_atom_per_verse,
            "max_verse_per_atom": max_verse_per_atom,
        },
        "summary": {
            "verse_nodes": len(verse_to_atoms),
            "atom_nodes": len(atom_to_verses),
        },
        "verse_to_atoms": verse_to_atoms,
        "atom_to_verses": atom_to_verses,
        "reproduce": "py scripts/build_logos_bidirectional_anchor_index_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-atom-per-verse", type=int, default=16)
    ap.add_argument("--max-verse-per-atom", type=int, default=24)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build(max_atom_per_verse=max(1, args.max_atom_per_verse), max_verse_per_atom=max(1, args.max_verse_per_atom))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool((doc.get("summary") or {}).get("verse_nodes"))
    print(json.dumps({"ok": ok, "summary": doc.get("summary"), "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
