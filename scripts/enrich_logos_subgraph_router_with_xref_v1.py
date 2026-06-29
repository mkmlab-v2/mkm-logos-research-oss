#!/usr/bin/env python3
"""Enrich themed subgraph GraphRAG router JSON with 1-hop xref neighbors."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PY = sys.executable
THEME_PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
DEFAULT_XREF_JSONL = ROOT / "docs/final/artifacts/logos_themed_xref_edges_v1.jsonl"
DEFAULT_XREF_MANIFEST = ROOT / "reports/logos_themed_xref_subgraph_v1_latest.json"

from scripts.build_logos_themed_xref_subgraph_v1 import _theme_anchor_ids
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _neighbors_for_theme(xref_rows: list[dict[str, Any]], theme_id: str) -> dict[str, list[dict[str, Any]]]:
    by_src: dict[str, list[dict[str, Any]]] = {}
    by_dst: dict[str, list[dict[str, Any]]] = {}
    for row in xref_rows:
        if row.get("theme_id") != theme_id:
            continue
        src = str(row.get("src_verse_id") or "")
        dst = str(row.get("dst_verse_id") or "")
        if src:
            by_src.setdefault(src, []).append(row)
        if dst:
            by_dst.setdefault(dst, []).append(row)
    for bucket in (by_src, by_dst):
        for key in bucket:
            bucket[key].sort(key=lambda r: int(r.get("votes") or 0), reverse=True)
    return {"by_src": by_src, "by_dst": by_dst}


def _xref_hits_for_anchor(
    anchor: str,
    *,
    xref_index: dict[str, dict[str, list[dict[str, Any]]]],
    max_neighbors: int,
) -> list[tuple[dict[str, Any], str]]:
    """Return (edge_row, neighbor_verse_id) pairs for one anchor."""
    hits: list[tuple[dict[str, Any], str]] = []
    by_src = xref_index["by_src"]
    by_dst = xref_index["by_dst"]
    for key in _lookup_aliases(anchor):
        for row in by_src.get(key, []):
            dst = str(row.get("dst_verse_id") or "")
            if dst:
                hits.append((row, dst))
        for row in by_dst.get(key, []):
            src = str(row.get("src_verse_id") or "")
            if src:
                hits.append((row, src))
    hits.sort(key=lambda pair: int(pair[0].get("votes") or 0), reverse=True)
    return hits[:max_neighbors]


def _lookup_aliases(vid: str) -> set[str]:
    out = {vid, canonical_verse_ref(vid)}
    if vid.startswith("Jhn."):
        out.add("John." + vid[4:])
    elif vid.startswith("John."):
        out.add("Jhn." + vid[5:])
    return {x for x in out if x}


def enrich_router(
    router_doc: dict[str, Any],
    *,
    theme_id: str,
    xref_index: dict[str, dict[str, list[dict[str, Any]]]],
    theme_anchor_ids: set[str],
    max_neighbors_per_anchor: int,
) -> dict[str, Any]:
    out = dict(router_doc)
    router_verse_ids = list(out.get("verse_ids") or [])
    anchor_keys = list(dict.fromkeys(router_verse_ids + sorted(theme_anchor_ids)))
    anchor_set = set(anchor_keys)
    xref_hits: list[dict[str, Any]] = []
    neighbor_ids: list[str] = []

    for anchor in anchor_keys:
        for row, dst in _xref_hits_for_anchor(
            anchor,
            xref_index=xref_index,
            max_neighbors=max_neighbors_per_anchor,
        ):
            if not dst or dst in anchor_set:
                continue
            xref_hits.append(
                {
                    "anchor_verse_id": anchor,
                    "neighbor_verse_id": dst,
                    "votes": row.get("votes"),
                    "direction": row.get("direction"),
                }
            )
            if dst not in neighbor_ids:
                neighbor_ids.append(dst)

    merged_ids = list(router_verse_ids)
    for nid in neighbor_ids:
        if nid not in merged_ids:
            merged_ids.append(nid)

    out["verse_ids"] = merged_ids
    out["xref_enrichment"] = {
        "schema": "logos_subgraph_xref_enrichment_v1",
        "theme_id": theme_id,
        "anchor_count": len(anchor_keys),
        "theme_anchor_count": len(theme_anchor_ids),
        "router_verse_count": len(router_verse_ids),
        "neighbor_count": len(neighbor_ids),
        "hits": xref_hits[:200],
        "source_manifest": "reports/logos_themed_xref_subgraph_v1_latest.json",
    }
    out["generated_at_utc"] = _utc()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--themes", default="dan_aramaic,john_1_logos")
    ap.add_argument("--xref-jsonl", type=Path, default=DEFAULT_XREF_JSONL)
    ap.add_argument("--run-router", action="store_true", default=True)
    ap.add_argument("--no-run-router", action="store_false", dest="run_router")
    ap.add_argument("--max-neighbors-per-anchor", type=int, default=5)
    args = ap.parse_args()

    presets = _load_json(THEME_PRESETS)
    if not presets:
        raise SystemExit(f"missing {THEME_PRESETS}")

    xref_rows = _load_jsonl(args.xref_jsonl)
    if not xref_rows:
        raise SystemExit(f"missing xref edges: {args.xref_jsonl}")

    results: list[dict[str, Any]] = []
    for theme_id in [t.strip() for t in args.themes.split(",") if t.strip()]:
        theme = (presets.get("themes") or {}).get(theme_id) or {}
        query = str(theme.get("graphrag_query_ko") or "")
        out_path = ROOT / f"docs/final/artifacts/logos_subgraph_graphrag_router_{theme_id}_latest.json"

        if args.run_router:
            proc = subprocess.run(
                [
                    PY,
                    "scripts/run_logos_subgraph_graphrag_router_v1.py",
                    "--query",
                    query,
                    "--output-json",
                    str(out_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise SystemExit(f"router failed {theme_id}: {proc.stderr}")

        router_doc = _load_json(out_path)
        if not router_doc:
            raise SystemExit(f"missing router: {out_path}")

        xref_index = _neighbors_for_theme(xref_rows, theme_id)
        theme_anchors = _theme_anchor_ids(presets, theme_id)
        enriched = enrich_router(
            router_doc,
            theme_id=theme_id,
            xref_index=xref_index,
            theme_anchor_ids=theme_anchors,
            max_neighbors_per_anchor=args.max_neighbors_per_anchor,
        )
        out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append(
            {
                "theme_id": theme_id,
                "out": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "neighbor_count": enriched["xref_enrichment"]["neighbor_count"],
                "verse_ids_total": len(enriched.get("verse_ids") or []),
            }
        )

    summary_path = ROOT / "reports/logos_themed_xref_router_enrichment_v1_latest.json"
    summary = {
        "schema": "logos_themed_xref_router_enrichment_v1",
        "generated_at_utc": _utc(),
        "results": results,
        "reproduce": "py scripts/enrich_logos_subgraph_router_with_xref_v1.py",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
