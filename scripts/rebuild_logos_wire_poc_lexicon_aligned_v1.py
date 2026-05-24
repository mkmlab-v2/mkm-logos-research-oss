#!/usr/bin/env python3
"""Rebuild logos graph wire POC with lexicon-known atom_ids only (B-track [HYPO])."""

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

DEFAULT_POC_IN = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_lexicon_aligned_v1_latest.json"
DEFAULT_LEX = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
ANCHOR07 = ROOT / "reports/constitution/btrack_pilot/comp_anchor07_wire_atom_candidates_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def filter_ids_to_lexicon(atom_ids: list[str], lexicon_path: Path) -> tuple[list[str], list[str]]:
    from scripts.core.master_codebook_lexicon_v1_bridge import _load_atom_id_to_form

    idx = _load_atom_id_to_form(str(lexicon_path.resolve()))
    known: list[str] = []
    dropped: list[str] = []
    seen: set[str] = set()
    for aid in atom_ids:
        key = str(aid)
        if key in seen:
            continue
        seen.add(key)
        if key in idx:
            known.append(key)
        else:
            dropped.append(key)
    return known, dropped


def anchor07_ids(*, max_n: int = 12) -> list[str]:
    if not ANCHOR07.is_file():
        return []
    doc = json.loads(ANCHOR07.read_text(encoding="utf-8"))
    return [str(x) for x in (doc.get("wire_atom_ids_candidates") or []) if x][:max_n]


def rebuild(
    poc_in: Path,
    *,
    lexicon_path: Path,
    strategy: str = "anchor07_primary",
) -> dict[str, Any]:
    base = json.loads(poc_in.read_text(encoding="utf-8"))
    gr = dict(base.get("graph_rag") or {})
    prior_path = list(gr.get("reasoning_path_node_ids") or [])

    if strategy == "anchor07_primary":
        aligned = anchor07_ids(max_n=12)
        dropped = [x for x in prior_path if x not in aligned]
    elif strategy == "filter_merged":
        from scripts.mkm_graph_wire_bridge_influence_v1 import wire_atom_ids_merged

        merged = wire_atom_ids_merged(anchor_max=32)
        aligned, dropped = filter_ids_to_lexicon(merged, lexicon_path)
    else:
        aligned, dropped = filter_ids_to_lexicon(prior_path, lexicon_path)

    out = dict(base)
    out["schema"] = "logos_graph_wire_rag_poc_lexicon_aligned_v1"
    out["generated_at_utc"] = _utc()
    out["hypothesis_tier"] = "[HYPO]"
    out["parent_poc"] = str(poc_in.relative_to(ROOT)).replace("\\", "/")
    out["alignment"] = {
        "strategy": strategy,
        "lexicon_path": str(lexicon_path.relative_to(ROOT)).replace("\\", "/"),
        "prior_reasoning_path_node_ids": prior_path,
        "dropped_unknown_to_lexicon": dropped,
        "aligned_count": len(aligned),
    }
    out["graph_rag"] = {
        **gr,
        "reasoning_path_node_ids": aligned,
        "verse_atom_ids_sampled": len(aligned),
    }
    out["policy"] = {
        **(base.get("policy") or {}),
        "research_only": True,
        "wire_atom_source": "comp_anchor07_wire_atom_candidates_v1 + lexicon SSOT",
    }
    out["boundary_ack"] = (
        "Lexicon-aligned wire POC: verse-level graph node ids replaced by token atom_ids "
        "present in master_codebook_lexicon_v1. B-track only; not Track A promotion."
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild logos wire POC lexicon-aligned (B-track)")
    ap.add_argument("--poc-in", type=Path, default=DEFAULT_POC_IN)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEX)
    ap.add_argument(
        "--strategy",
        choices=("anchor07_primary", "filter_merged"),
        default="anchor07_primary",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.poc_in.is_file():
        print(f"error: missing poc {args.poc_in}", file=sys.stderr)
        return 2
    if not args.lexicon.is_file():
        print(f"error: missing lexicon {args.lexicon}", file=sys.stderr)
        return 2

    doc = rebuild(args.poc_in, lexicon_path=args.lexicon, strategy=args.strategy)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "aligned_count": doc["alignment"]["aligned_count"],
                "dropped": doc["alignment"]["dropped_unknown_to_lexicon"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["alignment"]["aligned_count"] >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
