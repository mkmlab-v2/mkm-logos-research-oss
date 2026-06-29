"""Narrative-path lemma bridge PoC — bidirectional 41k atoms → sparse lemma edges (HYPO)."""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
BIDIRECTIONAL = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"
LEMMA_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
PATH_ID = "narrative_lemma_bridge_v1"


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


def _canon_verse(ref: str) -> str:
    from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

    return canonical_verse_ref(str(ref or "").strip())


def collect_narrative_verse_refs(bridge: dict[str, Any]) -> list[str]:
    verses: list[str] = []
    seen: set[str] = set()
    for sample in bridge.get("narrative_path_samples") or []:
        for hop in sample.get("path") or []:
            vr = _canon_verse(str(hop.get("verse_ref") or ""))
            if vr and vr not in seen:
                seen.add(vr)
                verses.append(vr)
    return verses


def collect_motif_tokens_by_verse(linked: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in linked:
        tokens = {_strip_accents(t) for t in row.get("motif_tokens") or [] if len(str(t)) >= 3}
        for vr in row.get("verse_refs") or []:
            canon = _canon_verse(str(vr))
            if not canon:
                continue
            bucket = out.setdefault(canon, set())
            bucket.update(tokens)
    return out


def _motif_boost(atom: dict[str, Any], motifs: set[str]) -> float:
    if not motifs:
        return 0.0
    norm = _strip_accents(str(atom.get("normalized_form") or ""))
    atom_id = _strip_accents(str(atom.get("atom_id") or "").split("::")[-1])
    for motif in motifs:
        if len(motif) < 3:
            continue
        if motif in norm or norm in motif or motif in atom_id or atom_id in motif:
            return 0.25
        if len(motif) >= 4 and (motif[:4] in norm or norm[:4] in motif):
            return 0.15
    return 0.0


def rank_atoms_for_verse(
    atoms: list[dict[str, Any]],
    *,
    motifs: set[str],
    max_atoms: int,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for atom in atoms:
        base = float(atom.get("weight") or 0.0)
        score = base + _motif_boost(atom, motifs)
        scored.append((score, atom))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [atom for _, atom in scored[:max_atoms]]


def _anchor_row_for_verse(per_anchor: list[dict[str, Any]], verse_ref: str) -> dict[str, Any] | None:
    for row in per_anchor:
        for vr in row.get("verse_refs") or []:
            if _canon_verse(str(vr)) == verse_ref:
                return row
    return None


def _proxy_verse_from_meaning_graph(anchor: dict[str, Any]) -> str | None:
    for edge in anchor.get("meaning_graph_edges") or []:
        if str(edge.get("edge_type") or "") != "shared_primitive_link":
            continue
        dst = str(edge.get("dst_node_id") or "")
        prefix = "cosmic_anchor_verse::"
        if dst.startswith(prefix):
            return _canon_verse(dst[len(prefix) :])
    return None


def build_narrative_bidirectional_lemma_edges(
    *,
    verse_refs: list[str],
    bidirectional: dict[str, list[dict[str, Any]]],
    motif_by_verse: dict[str, set[str]],
    max_atoms_per_verse: int = 8,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    edge_i = 0
    for verse_ref in verse_refs:
        atoms = bidirectional.get(verse_ref) or []
        if not atoms:
            continue
        motifs = motif_by_verse.get(verse_ref, set())
        picked = rank_atoms_for_verse(atoms, motifs=motifs, max_atoms=max_atoms_per_verse)
        for atom in picked:
            src = str(atom.get("atom_id") or "")
            if not src:
                continue
            weight = min(1.0, round(float(atom.get("weight") or 0.1) + _motif_boost(atom, motifs), 4))
            rows.append(
                {
                    "schema": "logos_lemma_verse_edge_v1",
                    "edge_id": f"lemma_verse::narrative_bi_{edge_i}",
                    "src_node_id": src,
                    "dst_node_id": verse_ref,
                    "edge_type": "BI_ATOM_CONTAIN",
                    "weight": weight,
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "path_id": PATH_ID,
                    "source_bridge": str(BIDIRECTIONAL.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            edge_i += 1
    return rows


def _lemma_edge_merge_key(row: dict[str, Any]) -> tuple[str, ...]:
    key: tuple[str, ...] = (
        str(row.get("src_node_id")),
        str(row.get("dst_node_id")),
        str(row.get("edge_type")),
    )
    if row.get("edge_type") == "INTER_HOP_BRIDGE_CONTAIN":
        key = key + (
            str(row.get("sample_id") or ""),
            str(row.get("pair_index") if row.get("pair_index") is not None else ""),
        )
    return key


def merge_jsonl(
    *,
    base_path: Path,
    new_rows: list[dict[str, Any]],
    strip_path_id: str | None = PATH_ID,
) -> tuple[list[dict[str, Any]], int]:
    existing: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    if base_path.is_file():
        for line in base_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if strip_path_id and row.get("path_id") == strip_path_id:
                continue
            key = _lemma_edge_merge_key(row)
            if key in seen:
                continue
            seen.add(key)
            existing.append(row)
    added = 0
    for row in new_rows:
        key = _lemma_edge_merge_key(row)
        if key in seen:
            continue
        seen.add(key)
        existing.append(row)
        added += 1
    return existing, added


def build_narrative_lemma_bridge_report(
    bridge: dict[str, Any] | None = None,
    *,
    bidirectional_path: Path = BIDIRECTIONAL,
    max_atoms_per_verse: int = 8,
) -> dict[str, Any]:
    bridge = bridge or json.loads(BRIDGE.read_text(encoding="utf-8"))
    bi_doc = json.loads(bidirectional_path.read_text(encoding="utf-8"))
    bidirectional = bi_doc.get("verse_to_atoms") or {}

    verse_refs = collect_narrative_verse_refs(bridge)
    per_anchor = list(bridge.get("per_anchor") or [])
    motif_by_verse = collect_motif_tokens_by_verse(per_anchor)
    edges = build_narrative_bidirectional_lemma_edges(
        verse_refs=verse_refs,
        bidirectional=bidirectional,
        motif_by_verse=motif_by_verse,
        max_atoms_per_verse=max_atoms_per_verse,
    )
    covered = {str(e.get("dst_node_id") or "") for e in edges}
    edge_i = len(edges)
    proxy_edge_count = 0
    for verse_ref in verse_refs:
        if verse_ref in covered or bidirectional.get(verse_ref):
            continue
        anchor = _anchor_row_for_verse(per_anchor, verse_ref)
        if not anchor:
            continue
        proxy = _proxy_verse_from_meaning_graph(anchor)
        if not proxy or not (bidirectional.get(proxy) or []):
            continue
        motifs = motif_by_verse.get(verse_ref, set())
        picked = rank_atoms_for_verse(
            bidirectional[proxy],
            motifs=motif_by_verse.get(proxy, set()) | motifs,
            max_atoms=min(3, max_atoms_per_verse),
        )
        for atom in picked:
            src = str(atom.get("atom_id") or "")
            if not src:
                continue
            weight = min(1.0, round(float(atom.get("weight") or 0.1) + _motif_boost(atom, motifs), 4))
            edges.append(
                {
                    "schema": "logos_lemma_verse_edge_v1",
                    "edge_id": f"lemma_verse::narrative_bi_proxy_{edge_i}",
                    "src_node_id": src,
                    "dst_node_id": verse_ref,
                    "edge_type": "BI_ATOM_PROXY_CONTAIN",
                    "weight": weight,
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "path_id": PATH_ID,
                    "proxy_verse_ref": proxy,
                    "source_bridge": str(bidirectional_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            edge_i += 1
            proxy_edge_count += 1
        covered.add(verse_ref)

    verses_with_edges = {str(e.get("dst_node_id") or "") for e in edges}
    verses_with_atoms = sum(1 for v in verse_refs if v in verses_with_edges)
    motif_boosted = sum(
        1
        for edge in edges
        if float(edge.get("weight") or 0) > float(bidirectional.get(edge["dst_node_id"], [{}])[0].get("weight") or 0)
    )

    return {
        "schema": "logos_narrative_lemma_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "note_ko": (
            "B-track PoC: 8 narrative paths × top bidirectional atoms (41k fuel index). "
            "NOT morphology-verified MACULA; NOT Track A promotion."
        ),
        "inputs": {
            "bidirectional_index": str(bidirectional_path.relative_to(ROOT)).replace("\\", "/"),
            "max_atoms_per_verse": max_atoms_per_verse,
            "narrative_verse_count": len(verse_refs),
        },
        "summary": {
            "edges_built": len(edges),
            "verses_with_atoms": verses_with_atoms,
            "verses_missing_atoms": len(verse_refs) - verses_with_atoms,
            "proxy_edge_count": proxy_edge_count,
            "motif_boosted_edge_count": motif_boosted,
        },
        "verse_refs": verse_refs,
        "edges": edges,
        "reproducible_command": "py scripts/run_logos_narrative_lemma_bridge_chain_v1.py",
    }
