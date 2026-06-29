"""Lemma anchor spike — bidirectional atoms for anchors below target (HYPO, B-track)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.logos_narrative_lemma_bridge_v1 import (
    BIDIRECTIONAL,
    LEMMA_EDGES,
    _canon_verse,
    build_narrative_bidirectional_lemma_edges,
    collect_motif_tokens_by_verse,
    merge_jsonl,
)
from scripts.core.logos_narrative_lemma_overlap_eval_v1 import load_bidirectional_atoms

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
PATH_ID_60 = "lemma_spike_60_v1"
PATH_ID_P5 = "lemma_spike_p5_v1"
PATH_ID_P6 = "lemma_spike_p6_v1"
PATH_ID_P7 = "lemma_spike_p7_v1"
PATH_ID_P8 = "lemma_spike_p8_v2"


def path_id_for_target(target_hits: int) -> str:
    if target_hits >= 339:
        return PATH_ID_P8
    if target_hits >= 300:
        return PATH_ID_P7
    if target_hits >= 200:
        return PATH_ID_P6
    if target_hits >= 100:
        return PATH_ID_P5
    return PATH_ID_60


def _narrative_anchor_ids(bridge: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for sample in bridge.get("narrative_path_samples") or []:
        for hop in sample.get("path") or []:
            aid = str(hop.get("anchor_id") or "")
            if aid:
                ids.add(aid)
    return ids


def _priority_anchor(row: dict[str, Any], narrative_ids: set[str]) -> tuple[int, str]:
    score = 0
    if str(row.get("anchor_id") or "") in narrative_ids:
        score += 200
    if int(row.get("meaning_graph_edge_count") or 0) > 0:
        score += 100
    if row.get("themed_bridge_ids"):
        score += 50
    if int(row.get("lemma_edge_count") or 0) > 0:
        score -= 1000
    return (-score, str(row.get("file_stem") or ""))


def select_spike_anchors(
    per_anchor: list[dict[str, Any]],
    *,
    narrative_ids: set[str],
    current_hits: int,
    target_hits: int,
) -> list[dict[str, Any]]:
    need = max(target_hits - current_hits, 0)
    if need <= 0:
        return []
    missing = [row for row in per_anchor if int(row.get("lemma_edge_count") or 0) == 0]
    missing.sort(key=lambda row: _priority_anchor(row, narrative_ids))
    return missing[: max(need + 25, need)]


def _proxy_verse_from_meaning_graph(anchor: dict[str, Any]) -> str | None:
    for edge in anchor.get("meaning_graph_edges") or []:
        if str(edge.get("edge_type") or "") != "shared_primitive_link":
            continue
        dst = str(edge.get("dst_node_id") or "")
        prefix = "cosmic_anchor_verse::"
        if dst.startswith(prefix):
            return _canon_verse(dst[len(prefix) :])
    return None


def build_spike_edges_for_anchors(
    anchors: list[dict[str, Any]],
    *,
    bidirectional: dict[str, list[dict[str, Any]]],
    motif_by_verse: dict[str, set[str]],
    max_atoms_per_verse: int = 6,
    path_id: str | None = None,
) -> list[dict[str, Any]]:
    path_id = path_id or PATH_ID_60
    rows: list[dict[str, Any]] = []
    for anchor in anchors:
        verse_refs: list[str] = []
        seen: set[str] = set()
        for vr in anchor.get("verse_refs") or []:
            canon = _canon_verse(str(vr))
            if canon and canon not in seen:
                seen.add(canon)
                verse_refs.append(canon)
        if not verse_refs:
            continue
        before = len(rows)
        batch = build_narrative_bidirectional_lemma_edges(
            verse_refs=verse_refs,
            bidirectional=bidirectional,
            motif_by_verse=motif_by_verse,
            max_atoms_per_verse=max_atoms_per_verse,
        )
        for row in batch:
            row["path_id"] = path_id
            row["edge_type"] = "BI_ATOM_SPIKE_CONTAIN"
            row["source_bridge"] = "scripts/core/logos_lemma_anchor_spike_v1.py"
            rows.append(row)
        if len(rows) > before:
            continue
        proxy = _proxy_verse_from_meaning_graph(anchor)
        if not proxy or not (bidirectional.get(proxy) or []):
            continue
        primary = verse_refs[0]
        proxy_batch = build_narrative_bidirectional_lemma_edges(
            verse_refs=[proxy],
            bidirectional=bidirectional,
            motif_by_verse=motif_by_verse,
            max_atoms_per_verse=min(3, max_atoms_per_verse),
        )
        for row in proxy_batch:
            row["dst_node_id"] = primary
            row["proxy_verse_ref"] = proxy
            row["path_id"] = path_id
            row["edge_type"] = "BI_ATOM_SPIKE_PROXY"
            row["source_bridge"] = "scripts/core/logos_lemma_anchor_spike_v1.py"
            rows.append(row)
    return rows


def build_lemma_spike_report(
    *,
    target_hits: int = 60,
    bridge: dict[str, Any] | None = None,
    path_id: str | None = None,
) -> dict[str, Any]:
    bridge = bridge or json.loads(BRIDGE.read_text(encoding="utf-8"))
    path_id = path_id or path_id_for_target(target_hits)
    per_anchor = list(bridge.get("per_anchor") or [])
    current_hits = int((bridge.get("summary") or {}).get("lemma_hit_anchors") or 0)
    narrative_ids = _narrative_anchor_ids(bridge)
    candidates = select_spike_anchors(
        per_anchor,
        narrative_ids=narrative_ids,
        current_hits=current_hits,
        target_hits=target_hits,
    )
    bidirectional = load_bidirectional_atoms(BIDIRECTIONAL)
    motif_by_verse = collect_motif_tokens_by_verse(per_anchor)
    edges = build_spike_edges_for_anchors(
        candidates,
        bidirectional=bidirectional,
        motif_by_verse=motif_by_verse,
        path_id=path_id,
    )
    return {
        "schema": "logos_lemma_anchor_spike_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "target_lemma_hit_anchors": target_hits,
        "baseline_lemma_hit_anchors": current_hits,
        "candidate_anchor_count": len(candidates),
        "candidate_anchor_ids": [str(r.get("anchor_id") or "") for r in candidates],
        "candidate_verse_count": len({vr for r in candidates for vr in r.get("verse_refs") or []}),
        "edges_built": len(edges),
        "path_id": path_id,
        "edges": edges,
        "reproducible_command": "py scripts/run_logos_lemma_60_chain_v1.py",
    }


def merge_spike_edges(edges: list[dict[str, Any]], *, path_id: str = PATH_ID_60) -> tuple[int, int]:
    merged, added = merge_jsonl(base_path=LEMMA_EDGES, new_rows=edges, strip_path_id=path_id)
    LEMMA_EDGES.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )
    return added, len(merged)
