#!/usr/bin/env python3
"""COMP-ANCHOR-05: single-pass full verse corpus scan → atom hit histogram (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor05_verse_pool_full_scan_v1.json"
REGISTRY = ROOT / "docs/final/artifacts/atom_anchor_registry_v1.json"
DEFAULT_VERSE = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _registry_atom_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    ids: list[str] = []
    for row in doc.get("atoms") or []:
        if isinstance(row, dict) and row.get("atom_id"):
            ids.append(str(row["atom_id"]))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verse-jsonl", default=str(DEFAULT_VERSE))
    parser.add_argument("--registry-json", default=str(REGISTRY))
    parser.add_argument("--out-json", default=str(OUT))
    parser.add_argument("--top-k", type=int, default=50)
    args = parser.parse_args()

    verse_path = Path(args.verse_jsonl)
    if not verse_path.is_absolute():
        verse_path = ROOT / verse_path
    if not verse_path.is_file():
        print(f"missing verse jsonl: {verse_path}", file=sys.stderr)
        return 1

    from scripts.project_logos_verse_4d_to_lexicon_v1 import (  # noqa: WPS433
        _iter_jsonl,
        load_form_to_entry,
        token_atom_counts,
    )
    from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: WPS433
        resolve_latest_codebook_path,
    )

    codebook_path = resolve_latest_codebook_path()
    if codebook_path is None or not codebook_path.is_file():
        print("missing master_codebook_lexicon_v1", file=sys.stderr)
        return 1

    form_to_entry = load_form_to_entry(codebook_path)
    registry_ids = _registry_atom_ids(ROOT / args.registry_json)

    verses_scanned = 0
    verses_with_any_atom = 0
    atom_verse_hits: Counter[str] = Counter()

    for row in _iter_jsonl(verse_path):
        if row.get("schema") != "logos_verse_4d_v1":
            continue
        verses_scanned += 1
        text_span = row.get("text_span") or {}
        text = (
            str(text_span.get("original_script_text") or "")
            if isinstance(text_span, dict)
            else ""
        )
        counts = token_atom_counts(text, form_to_entry)
        if not counts:
            continue
        verses_with_any_atom += 1
        for aid, hits in counts.items():
            if int(hits) >= 1:
                atom_verse_hits[str(aid)] += 1

    top = [
        {"atom_id": aid, "verses_with_hits": n}
        for aid, n in atom_verse_hits.most_common(max(1, args.top_k))
    ]
    registry_rows: list[dict[str, Any]] = []
    for aid in registry_ids:
        registry_rows.append(
            {
                "atom_id": aid,
                "codebook_known": aid in {str(e.get("atom_id")) for e in form_to_entry.values()},
                "verses_with_hits": int(atom_verse_hits.get(aid) or 0),
            }
        )

    report = {
        "schema": "comp_anchor05_verse_pool_full_scan_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
        },
        "inputs": {
            "verse_jsonl": str(verse_path.relative_to(ROOT)).replace("\\", "/"),
            "codebook_path": str(codebook_path.relative_to(ROOT)).replace("\\", "/"),
            "registry_json": str(Path(args.registry_json)).replace("\\", "/"),
        },
        "summary": {
            "verses_scanned": verses_scanned,
            "verses_with_any_lexicon_atom": verses_with_any_atom,
            "unique_atoms_with_verse_hits": len(atom_verse_hits),
            "codebook_forms_loaded": len(form_to_entry),
        },
        "registry_atoms": registry_rows,
        "top_atoms_by_verse_hits": top,
        "note": (
            "Full single-pass scan (max_rows=0). Conceptual registry atoms are English labels; "
            "verse hits require matching master_codebook atom_id forms in original script."
        ),
    }

    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "verses_scanned": verses_scanned,
                "unique_atoms": len(atom_verse_hits),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
