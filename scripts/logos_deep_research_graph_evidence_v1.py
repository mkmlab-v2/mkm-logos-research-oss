#!/usr/bin/env python3
"""Track B — graph-backed evidence for logos_deep_research_distill (no LLM)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_VERSE_JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
VERSE_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.\d+\.\d+$")
THEME_PRESETS_PATH = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"


def load_theme_preset(theme_id: str, presets_path: Path = THEME_PRESETS_PATH) -> dict[str, Any]:
    if not presets_path.is_file():
        raise FileNotFoundError(f"Missing theme presets: {presets_path}")
    doc = json.loads(presets_path.read_text(encoding="utf-8"))
    themes = doc.get("themes") or {}
    if theme_id not in themes:
        raise KeyError(f"Unknown theme_id: {theme_id}")
    return dict(themes[theme_id])


def _edge_matches_prefix(edge: dict[str, Any], prefix: str) -> bool:
    for key in ("src_node_id", "dst_node_id"):
        vid = verse_id_from_node(str(edge.get(key) or ""))
        if vid and vid.startswith(prefix):
            return True
    return False


def iter_edges_for_theme(
    edges_path: Path,
    *,
    verse_prefix: str,
    max_edges: int = 24,
    min_weight: float = 0.72,
) -> list[dict[str, Any]]:
    if not edges_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in edges_path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if verse_prefix and not _edge_matches_prefix(row, verse_prefix):
            continue
        w = float(row.get("weight") or 0.0)
        if w < min_weight:
            continue
        rows.append(row)
    rows.sort(key=lambda r: float(r.get("weight") or 0.0), reverse=True)
    return rows[:max_edges]


def load_verse_ids_by_prefix(
    prefix: str,
    jsonl_path: Path = DEFAULT_VERSE_JSONL,
    *,
    max_verses: int = 32,
) -> list[str]:
    if not prefix or not jsonl_path.is_file():
        return []
    found: list[str] = []
    for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines():
        if len(found) >= max_verses:
            break
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid.startswith(prefix):
            found.append(vid)
    return found


def build_sequential_paths(verse_ids: list[str]) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for i in range(len(verse_ids) - 1):
        src, dst = verse_ids[i], verse_ids[i + 1]
        paths.append(
            {
                "path_id": f"gp_seq_{i + 1:03d}",
                "edge_type": "sequential_reading",
                "verse_ids": [src, dst],
                "weight": 0.75,
                "confidence": 0.7,
                "evidence_snippet": "sequential verse chain (corpus fallback, no graph edge)",
                "relation_basis": ["corpus_sequence"],
                "hypothesis_tier": "B",
                "research_only": True,
            }
        )
    return paths[:24]


def verse_id_from_node(node_id: str) -> str | None:
    if not isinstance(node_id, str):
        return None
    tail = node_id.split("::", 1)[-1].strip()
    return tail if VERSE_REF_RE.match(tail) else None


def quote_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def load_verse_rows(verse_ids: set[str], jsonl_path: Path = DEFAULT_VERSE_JSONL) -> dict[str, dict[str, Any]]:
    if not verse_ids or not jsonl_path.is_file():
        return {}
    found: dict[str, dict[str, Any]] = {}
    remaining = set(verse_ids)
    for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines():
        if not remaining:
            break
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid in remaining:
            found[vid] = row
            remaining.discard(vid)
    return found


def iter_top_edges(
    edges_path: Path,
    *,
    max_edges: int = 24,
    min_weight: float = 0.72,
) -> list[dict[str, Any]]:
    if not edges_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in edges_path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        w = float(row.get("weight") or 0.0)
        if w < min_weight:
            continue
        rows.append(row)
    rows.sort(key=lambda r: float(r.get("weight") or 0.0), reverse=True)
    return rows[:max_edges]


def build_graph_paths(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for i, edge in enumerate(edges, start=1):
        src = verse_id_from_node(str(edge.get("src_node_id") or ""))
        dst = verse_id_from_node(str(edge.get("dst_node_id") or ""))
        if not src or not dst:
            continue
        paths.append(
            {
                "path_id": f"gp_{i:03d}",
                "edge_type": edge.get("edge_type"),
                "verse_ids": [src, dst],
                "weight": edge.get("weight"),
                "confidence": edge.get("confidence"),
                "evidence_snippet": edge.get("evidence"),
                "relation_basis": edge.get("relation_basis"),
                "hypothesis_tier": "B",
                "research_only": True,
            }
        )
    return paths


def build_evidence_refs(
    verse_rows: dict[str, dict[str, Any]],
    *,
    max_refs: int = 32,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for vid in sorted(verse_rows.keys())[:max_refs]:
        row = verse_rows[vid]
        surface = str(row.get("original_text") or row.get("text") or "")
        refs.append(
            {
                "verse_id": vid,
                "quote_hash": quote_hash(surface) if surface else None,
                "hash_tagged_snippet": surface[:120] if surface else "",
                "edition": row.get("edition"),
                "hebrew_value": row.get("hebrew_value"),
                "greek_value": row.get("greek_value"),
            }
        )
    return refs


def mean_4d_from_rows(verse_rows: dict[str, dict[str, Any]]) -> dict[str, float]:
    keys = ("S", "L", "K", "M")
    acc = {k: 0.0 for k in keys}
    n = 0
    for row in verse_rows.values():
        v4 = row.get("vector_4d")
        if not isinstance(v4, dict):
            continue
        try:
            for k in keys:
                acc[k] += float(v4.get(k) or 0.0)
            n += 1
        except (TypeError, ValueError):
            continue
    if n == 0:
        return {k: 0.0 for k in keys}
    return {k: acc[k] / n for k in keys}


def build_enriched_distill_fields(
    *,
    bundle_path: Path,
    edges_path: Path = DEFAULT_EDGES,
    verse_jsonl: Path = DEFAULT_VERSE_JSONL,
    max_edges: int = 24,
    theology_baseline_path: Path | None = None,
    theme_id: str | None = None,
    verse_prefix: str | None = None,
    min_weight: float | None = None,
    fallback_sequential_verses: bool = False,
    max_verses: int = 32,
) -> dict[str, Any]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    slice_id = "slice6_graph_enriched_distill"
    theme_title = ""
    if theme_id:
        preset = load_theme_preset(theme_id)
        verse_prefix = str(preset.get("verse_prefix") or verse_prefix or "")
        slice_id = str(preset.get("slice_id") or slice_id)
        theme_title = str(preset.get("title_ko") or theme_id)
        if min_weight is None:
            min_weight = float(preset.get("min_weight") or 0.72)
        if preset.get("fallback_sequential_verses"):
            fallback_sequential_verses = True
        if preset.get("max_verses"):
            max_verses = int(preset["max_verses"])
    if min_weight is None:
        min_weight = 0.72

    if verse_prefix:
        edges = iter_edges_for_theme(
            edges_path,
            verse_prefix=verse_prefix,
            max_edges=max_edges,
            min_weight=min_weight,
        )
    else:
        edges = iter_top_edges(edges_path, max_edges=max_edges, min_weight=min_weight)

    paths = build_graph_paths(edges)
    verse_ids: set[str] = set()
    for p in paths:
        for vid in p.get("verse_ids") or []:
            if isinstance(vid, str):
                verse_ids.add(vid)

    if fallback_sequential_verses and verse_prefix and len(paths) < 2:
        seq_ids = load_verse_ids_by_prefix(verse_prefix, verse_jsonl, max_verses=max_verses)
        if len(seq_ids) >= 2:
            paths = build_sequential_paths(seq_ids)
            verse_ids = set(seq_ids)

    verse_rows = load_verse_rows(verse_ids, verse_jsonl)
    evidence_refs = build_evidence_refs(verse_rows)
    mean_4d = mean_4d_from_rows(verse_rows)
    n_paths = len(paths)
    n_refs = len(evidence_refs)
    sufficient = n_refs >= 3 and n_paths >= 2
    uncertainty = max(0.15, 1.0 - min(0.85, 0.08 * n_refs + 0.05 * n_paths))

    theology_note = ""
    if theology_baseline_path and theology_baseline_path.is_file():
        try:
            tb = json.loads(theology_baseline_path.read_text(encoding="utf-8"))
            theology_note = str(tb.get("interpretation_policy_ko") or tb.get("note_ko") or "")[:240]
        except (json.JSONDecodeError, OSError):
            theology_note = ""

    return {
        "source_slice": {
            "slice_id": slice_id,
            "description": (
                f"theme={theme_id} graph+corpus enrichment"
                if theme_id
                else "graph path + verse anchor enrichment (deterministic)"
            ),
            "row_count": n_refs,
            "theme_id": theme_id,
            "theme_title_ko": theme_title or None,
        },
        "state_vector_logos": {"mean_4d": mean_4d},
        "epistemic_uncertainty": round(uncertainty, 4),
        "veto_flags": {
            "insufficient_evidence": not sufficient,
            "batch_too_small": n_refs < 8,
            "hash_coverage_below_min": n_refs < 3,
            "policy_violation": False,
        },
        "evidence_refs": evidence_refs,
        "graph_paths": paths,
        "mkm_interpretation_stub_ko": {
            "labels": ["TRACK_B", "HYPO", "NON_GATING"],
            "worldview_pointer": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
            "theology_baseline_pointer": "docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json",
            "frame_ko": (
                "[HYPO] Logos=말씀·초압축에서 펼쳐진 질서; 역추론은 신앙·해석 프레임이며 "
                "아래 graph_paths·evidence_refs는 원어·경로 근거만 제공한다."
            ),
            "theology_policy_snip_ko": theology_note,
            "graph_path_count": n_paths,
            "commander_adoption": "pending",
        },
        "review_gate": {
            "status": "required",
            "reason_code": "graph_enriched_first_pass",
            "notes": "지휘관 채택 전; Track A·실매매 트리거 금지",
        },
    }
