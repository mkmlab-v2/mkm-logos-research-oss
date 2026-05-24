#!/usr/bin/env python3
"""DF-P2-01: Resolve verse pool for a single codebook atom_id (lazy scan, no merge)."""

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
SCHEMA = "logos_atom_anchor_verse_pool_v1"
VERSION = "1.0.0"


def _rel_path(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _resolve_paths_from_registry() -> tuple[Path, Path | None]:
    from scripts.mkm_unified_asset_registry_v1 import resolve_lane  # noqa: WPS433

    corpus = resolve_lane("corpus_core_31k")
    verse_path: Path | None = None
    for pref in corpus.paths:
        if pref.key == "verse_4d_jsonl" and pref.exists:
            verse_path = pref.path
            break
    lex = resolve_lane("lexicon_master_41k")
    codebook: Path | None = None
    for pref in lex.paths:
        if pref.key == "lexicon_rows" and pref.exists:
            codebook = pref.path
            break
    if verse_path is None:
        verse_path = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
    return verse_path, codebook


def _load_registry_atom_ids(registry_path: Path) -> set[str]:
    if not registry_path.is_file():
        return set()
    doc = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    ids: set[str] = set()
    for row in doc.get("atoms") or []:
        if isinstance(row, dict) and row.get("atom_id"):
            ids.add(str(row["atom_id"]))
    return ids


def build_verse_pool(
    atom_id: str,
    *,
    verse_jsonl: Path,
    codebook_json: Path | None,
    max_rows: int = 0,
    min_hits: int = 1,
) -> dict[str, Any]:
    from scripts.project_logos_verse_4d_to_lexicon_v1 import (  # noqa: WPS433
        _iter_jsonl,
        load_form_to_entry,
        token_atom_counts,
    )
    from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: WPS433
        resolve_latest_codebook_path,
    )

    if codebook_json is None or not codebook_json.is_file():
        codebook_json = resolve_latest_codebook_path()
    if codebook_json is None or not codebook_json.is_file():
        raise FileNotFoundError("no master_codebook_lexicon_v1 codebook path")

    form_to_entry = load_form_to_entry(codebook_json)
    if atom_id not in {str(e.get("atom_id")) for e in form_to_entry.values()}:
        return {
            "atom_id": atom_id,
            "codebook_known": False,
            "verse_pool": [],
            "verses_scanned": 0,
            "codebook_path": _rel_path(codebook_json),
        }

    pool: list[dict[str, Any]] = []
    scanned = 0
    for row in _iter_jsonl(verse_jsonl):
        if max_rows and scanned >= max_rows:
            break
        if row.get("schema") != "logos_verse_4d_v1":
            continue
        scanned += 1
        text_span = row.get("text_span") or {}
        text = str(text_span.get("original_script_text") or "") if isinstance(text_span, dict) else ""
        counts = token_atom_counts(text, form_to_entry)
        hits = int(counts.get(atom_id) or 0)
        if hits < min_hits:
            continue
        total = sum(counts.values()) or 1
        pool.append(
            {
                "verse_id": str(row.get("verse_id") or ""),
                "token_hits": hits,
                "atom_weight_in_verse": round(hits / total, 8),
            }
        )

    pool.sort(key=lambda x: (-x["token_hits"], x["verse_id"]))
    return {
        "atom_id": atom_id,
        "codebook_known": True,
        "verse_pool": pool,
        "verse_count": len(pool),
        "verses_scanned": scanned,
        "codebook_path": _rel_path(codebook_json),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atom-id", required=True, help="master_codebook atom_id e.g. hebrew::ברא")
    parser.add_argument("--verse-jsonl", default="", help="Override verse jsonl (default: unified registry)")
    parser.add_argument("--codebook-json", default="", help="Override codebook JSON")
    parser.add_argument("--registry-json", default="docs/final/artifacts/atom_anchor_registry_v1.json")
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_atom_anchor_verse_pool_v1_latest.json",
    )
    parser.add_argument("--max-rows", type=int, default=0, help="0 = scan all (can be slow)")
    parser.add_argument("--min-hits", type=int, default=1)
    args = parser.parse_args()

    if args.verse_jsonl.strip() and args.codebook_json.strip():
        verse_path = Path(args.verse_jsonl)
        if not verse_path.is_absolute():
            verse_path = ROOT / verse_path
        codebook_path = Path(args.codebook_json)
        if not codebook_path.is_absolute():
            codebook_path = ROOT / codebook_path
    else:
        verse_path, codebook_path = _resolve_paths_from_registry()
        if args.verse_jsonl.strip():
            verse_path = ROOT / args.verse_jsonl
        if args.codebook_json.strip():
            codebook_path = ROOT / args.codebook_json

    if not verse_path.is_file():
        print(f"missing verse jsonl: {verse_path}", file=sys.stderr)
        return 1

    registry_ids = _load_registry_atom_ids(ROOT / args.registry_json)
    pool_doc = build_verse_pool(
        args.atom_id.strip(),
        verse_jsonl=verse_path,
        codebook_json=codebook_path,
        max_rows=max(0, args.max_rows),
        min_hits=max(1, args.min_hits),
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
        },
        "inputs": {
            "verse_jsonl": _rel_path(verse_path),
            "atom_id": args.atom_id.strip(),
            "registry_conceptual_atom": args.atom_id.strip() in registry_ids,
        },
        "pool": pool_doc,
        "boundary_ack": "Verse pool from token∩lexicon scan only; not IMF query or Track A.",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = pool_doc.get("codebook_known") and (
        pool_doc.get("verse_count", 0) > 0 or args.max_rows > 0
    )
    print(
        json.dumps(
            {
                "ok": pool_doc.get("codebook_known", False),
                "verse_count": pool_doc.get("verse_count", 0),
                "verses_scanned": pool_doc.get("verses_scanned", 0),
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if pool_doc.get("codebook_known") else 1


if __name__ == "__main__":
    raise SystemExit(main())
