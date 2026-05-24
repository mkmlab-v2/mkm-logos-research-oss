#!/usr/bin/env python3
"""COMP-ANCHOR-07: top hebrew/greek atoms from full scan as wire_atom_ids candidates ([HYPO], B-track)."""

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

SCAN = ROOT / "reports/constitution/btrack_pilot/comp_anchor05_verse_pool_full_scan_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor07_wire_atom_candidates_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_lang_atom(atom_id: str) -> bool:
    return atom_id.startswith("hebrew::") or atom_id.startswith("greek::")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-json", default=str(SCAN))
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--out-json", default=str(OUT))
    args = parser.parse_args()

    scan_path = Path(args.scan_json)
    if not scan_path.is_absolute():
        scan_path = ROOT / scan_path
    if not scan_path.is_file():
        print(json.dumps({"error": f"missing {scan_path}"}, ensure_ascii=False))
        return 2

    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    tops = [
        row
        for row in (scan.get("top_atoms_by_verse_hits") or [])
        if isinstance(row, dict) and _is_lang_atom(str(row.get("atom_id") or ""))
    ][: max(1, args.top_n)]

    candidates = [
        {
            "atom_id": str(r["atom_id"]),
            "verses_with_hits": r.get("verses_with_hits"),
            "use": "wire_atom_ids_candidate_only",
        }
        for r in tops
    ]

    doc: dict[str, Any] = {
        "schema": "comp_anchor07_wire_atom_candidates_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "track_wall": {
            "must_keep_auto_inject": False,
            "track_a_promotion": False,
        },
        "inputs": {"scan_json": str(scan_path.relative_to(ROOT)).replace("\\", "/")},
        "top_n": len(candidates),
        "wire_atom_ids_candidates": [c["atom_id"] for c in candidates],
        "candidates": candidates,
        "note": (
            "PoC extension for mkm_graph_wire_bridge_influence_v1.wire_atom_ids; "
            "does not replace graph_rag reasoning_path_node_ids from comp_atom05 PoC."
        ),
    }

    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(out_path.relative_to(ROOT)), "count": len(candidates)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
