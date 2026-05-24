#!/usr/bin/env python3
"""Append Logos theme seeds from completion catalog (Track B NON_GATING)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPEND = ROOT / "docs/research/logos_metaphor_db_v1/theme_backlog_seed_pool_v1_append.jsonl"
DB = ROOT / "docs/research/logos_metaphor_db_v1"
DEFAULT_CATALOG = ROOT / "scripts/data/logos_theme_completion_catalog_v1.json"

NODE_REF_POOL = [
    ("시편 119:105", "주의 말씀은 내 발에 등이요"),
    ("잠언 3:5", "너는 마음을 다하여 여호와를 신뢰하라"),
    ("이사야 40:31", "오직 여호와를 앙망하는 자는"),
    ("로마서 8:28", "모든 것이 합력하여"),
]


def row(slug, theme, ref, text, nid, note, nodes):
    return {
        "slug": slug,
        "status": "pending",
        "theme": theme,
        "anchor_ref": ref,
        "anchor_text": text,
        "anchor_node_id": nid,
        "ops_analogy_note": note,
        "semantic_nodes": nodes,
    }


def n(ref, text, edge, conn, domain):
    return {
        "ref": ref,
        "text": text,
        "edge_type": edge,
        "research_metaphor_logic_connection": conn,
        "research_metaphor_domain": domain,
    }


def _anchor_id(slug: str) -> str:
    return "ANCHOR_" + slug.upper().replace("-", "_")


def _nodes_for(slug: str, anchor_ref: str, anchor_text: str) -> list[dict]:
    dom = f"research_metaphor_{slug}"
    edges = [
        ("is_linked_to", "anchor link — ops metaphor"),
        ("supports_anchor", "support link — ops metaphor"),
        ("context_for", "context link — ops metaphor"),
        ("echoes_anchor", "echo link — ops metaphor"),
    ]
    refs = [
        (anchor_ref, anchor_text[:40]),
        NODE_REF_POOL[0],
        NODE_REF_POOL[1],
        NODE_REF_POOL[2],
    ]
    out = []
    for i, ((ref, text), (edge, conn)) in enumerate(zip(refs, edges)):
        out.append(n(ref, text, edge, conn, dom))
    return out


def _entry_from_catalog(item: dict) -> dict:
    slug = str(item["slug"])
    return row(
        slug,
        str(item["theme"]),
        str(item["anchor_ref"]),
        str(item["anchor_text"]),
        _anchor_id(slug),
        str(item["note"]),
        _nodes_for(slug, str(item["anchor_ref"]), str(item["anchor_text"])),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--all", action="store_true", help="Append entire catalog not yet on disk")
    ap.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Catalog JSON path (e.g. scripts/data/logos_theme_completion_catalog_v2.json)",
    )
    args = ap.parse_args()

    catalog_path = args.catalog if args.catalog.is_absolute() else ROOT / args.catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    existing_seed: set[str] = set()
    if APPEND.is_file():
        for line in APPEND.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_seed.add(json.loads(line).get("slug", ""))

    pending = [c for c in catalog if c["slug"] not in slugs]
    if args.all:
        batch = pending
    else:
        batch = pending[args.offset : args.offset + args.limit]

    added = 0
    with APPEND.open("a", encoding="utf-8") as fh:
        for item in batch:
            slug = item["slug"]
            if slug in slugs or slug in existing_seed:
                continue
            fh.write(json.dumps(_entry_from_catalog(item), ensure_ascii=False) + "\n")
            existing_seed.add(slug)
            added += 1
    print(f"appended {added} seeds (catalog remaining {len(pending) - added})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
