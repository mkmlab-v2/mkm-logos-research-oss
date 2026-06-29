"""Enrich bible_meaning_graph with cosmic-anchor verse nodes (HYPO, B-track)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.core.logos_verse_corpus_lookup_v1 import normalize_verse_ref
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

NODE_SCHEMA = "logos_cosmic_anchor_verse_node_v1"
EDGE_SCHEMA = "bible_meaning_graph_edge_v1"


def _top_primitive(anchor: dict[str, Any]) -> str | None:
    rows = anchor.get("kernel_alignment") or []
    if not rows:
        return None
    top = max(rows, key=lambda r: float(r.get("similarity_adjusted", r.get("similarity", 0))))
    prim = str(top.get("primitive") or "").strip()
    return prim or None


def _regime_hint(anchor: dict[str, Any]) -> str | None:
    sasang = (anchor.get("layers") or {}).get("sasang_myeongni_layer") or {}
    hint = str(sasang.get("ohaeng_hint") or "").strip()
    return hint or None


def _collect_anchor_verse_rows(
    batch_dir: Path,
    stems: list[str],
) -> list[tuple[str, str, dict[str, Any]]]:
    """Return (stem, verse_ref, anchor) for each anchor primary verse."""
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for stem in stems:
        path = batch_dir / f"{stem}.json"
        if not path.is_file():
            continue
        anchor = json.loads(path.read_text(encoding="utf-8"))
        refs = anchor.get("verse_refs") or []
        if not refs:
            continue
        vr = canonical_verse_ref(normalize_verse_ref(str(refs[0])))
        if vr:
            rows.append((stem, vr, anchor))
    return rows


def build_cosmic_anchor_verse_enrichment(
    *,
    batch_dir: Path,
    stems: list[str],
    existing_refs: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Materialize verse nodes + theme/regime/primitive edges for uncovered anchor refs."""
    anchor_rows = _collect_anchor_verse_rows(batch_dir, stems)
    new_nodes: list[dict[str, Any]] = []
    new_edges: list[dict[str, Any]] = []
    ref_to_stem: dict[str, str] = {}
    primitive_to_refs: dict[str, list[str]] = defaultdict(list)

    for stem, vr, anchor in anchor_rows:
        ref_to_stem[vr] = stem
        prim = _top_primitive(anchor)
        if prim:
            primitive_to_refs[prim].append(vr)
        if vr in existing_refs:
            continue
        node_id = f"cosmic_anchor_verse::{vr}"
        theme_tags = [prim] if prim else []
        regime_tags = []
        regime = _regime_hint(anchor)
        if regime:
            regime_tags.append(regime)
        new_nodes.append(
            {
                "schema": NODE_SCHEMA,
                "node_id": node_id,
                "ref": vr,
                "source_track": "B",
                "research_only": True,
                "hypothesis_class": "HYPO",
                "anchor_file_stem": stem,
                "theme_tags": theme_tags,
                "regime_tags": regime_tags,
            }
        )
        existing_refs.add(vr)
        if prim:
            tid = f"theme::{prim}"
            new_nodes.append(
                {
                    "schema": "bible_meaning_graph_node_v1",
                    "node_id": tid,
                    "kind": "theme",
                    "label": prim,
                }
            )
            new_edges.append(
                {
                    "schema": EDGE_SCHEMA,
                    "src_node_id": node_id,
                    "dst_node_id": tid,
                    "edge_type": "theme_association",
                    "weight": 0.55,
                    "hypothesis_class": "HYPO",
                }
            )
        if regime:
            rid = f"regime::{regime}"
            new_nodes.append(
                {
                    "schema": "bible_meaning_graph_node_v1",
                    "node_id": rid,
                    "kind": "regime",
                    "label": regime,
                }
            )
            new_edges.append(
                {
                    "schema": EDGE_SCHEMA,
                    "src_node_id": node_id,
                    "dst_node_id": rid,
                    "edge_type": "regime_projection",
                    "weight": 0.5,
                    "hypothesis_class": "HYPO",
                }
            )

    # Primitive co-occurrence edges (limited pairs per primitive)
    for prim, refs in primitive_to_refs.items():
        uniq = sorted(set(refs))
        if len(uniq) < 2:
            continue
        for i, src_ref in enumerate(uniq[:12]):
            for dst_ref in uniq[i + 1 : i + 3]:
                new_edges.append(
                    {
                        "schema": EDGE_SCHEMA,
                        "src_node_id": f"cosmic_anchor_verse::{src_ref}",
                        "dst_node_id": f"cosmic_anchor_verse::{dst_ref}",
                        "edge_type": "shared_primitive_link",
                        "weight": 0.45,
                        "hypothesis_class": "HYPO",
                        "reason": f"shared_primitive:{prim}",
                    }
                )

    return _dedupe_nodes(new_nodes), _dedupe_edges(new_edges)


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in nodes:
        nid = str(row.get("node_id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)
        out.append(row)
    return out


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in edges:
        key = (
            str(row.get("src_node_id") or ""),
            str(row.get("dst_node_id") or ""),
            str(row.get("edge_type") or ""),
        )
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def load_existing_verse_refs(nodes_path: Path) -> set[str]:
    refs: set[str] = set()
    if not nodes_path.is_file():
        return refs
    for line in nodes_path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ref = row.get("ref")
        if isinstance(ref, str) and ref.strip():
            refs.add(canonical_verse_ref(normalize_verse_ref(ref.strip())))
            continue
        nid = str(row.get("node_id") or "")
        if "::" in nid:
            tail = nid.split("::", 1)[1]
            refs.add(canonical_verse_ref(normalize_verse_ref(tail)))
    return refs


def merge_jsonl(
    path: Path,
    new_rows: list[dict[str, Any]],
    *,
    key_field: str = "node_id",
) -> int:
    """Append rows whose key_field is not already present. Returns appended count."""
    existing_keys: set[str] = set()
    lines: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = str(row.get(key_field) or "")
            if key:
                existing_keys.add(key)
            lines.append(line)
    appended = 0
    for row in new_rows:
        key = str(row.get(key_field) or "")
        if not key or key in existing_keys:
            continue
        lines.append(json.dumps(row, ensure_ascii=False))
        existing_keys.add(key)
        appended += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return appended


def merge_edges_jsonl(path: Path, new_rows: list[dict[str, Any]]) -> int:
    seen: set[tuple[str, str, str]] = set()
    lines: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                str(row.get("src_node_id") or ""),
                str(row.get("dst_node_id") or ""),
                str(row.get("edge_type") or ""),
            )
            if key[0] and key[1]:
                seen.add(key)
            lines.append(line)
    appended = 0
    for row in new_rows:
        key = (
            str(row.get("src_node_id") or ""),
            str(row.get("dst_node_id") or ""),
            str(row.get("edge_type") or ""),
        )
        if not key[0] or not key[1] or key in seen:
            continue
        lines.append(json.dumps(row, ensure_ascii=False))
        seen.add(key)
        appended += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return appended
