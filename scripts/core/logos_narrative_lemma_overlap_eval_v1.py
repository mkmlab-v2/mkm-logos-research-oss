"""B-track narrative × lemma overlap eval (HYPO) — 41k lexicon join vs 8 narrative paths."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
LEMMA_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
BIDIRECTIONAL = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"
LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"

_VERSE_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _canon_verse(ref: str) -> str:
    from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

    return canonical_verse_ref(str(ref or "").strip())


def _is_verse_ref(ref: str) -> bool:
    return bool(ref and _VERSE_RE.match(ref))


def load_lemma_verse_index(path: Path = LEMMA_EDGES) -> dict[str, list[dict[str, Any]]]:
    verse_to_lemmas: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not path.is_file():
        return verse_to_lemmas
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        dst = _canon_verse(str(row.get("dst_node_id") or ""))
        if not _is_verse_ref(dst):
            continue
        verse_to_lemmas[dst].append(
            {
                "src_node_id": row.get("src_node_id"),
                "edge_type": row.get("edge_type"),
                "weight": row.get("weight"),
                "path_id": row.get("path_id"),
                "sample_id": row.get("sample_id"),
                "pair_index": row.get("pair_index"),
            }
        )
    return verse_to_lemmas


def load_bidirectional_atoms(path: Path = BIDIRECTIONAL) -> dict[str, list[dict[str, Any]]]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("verse_to_atoms") or {}
    return {str(k): list(v or []) for k, v in raw.items()}


def _atom_id_set(atoms: list[dict[str, Any]]) -> set[str]:
    return {str(a.get("atom_id") or "") for a in atoms if a.get("atom_id")}


def _lemma_src_set(lemmas: list[dict[str, Any]]) -> set[str]:
    return {str(x.get("src_node_id") or "") for x in lemmas if x.get("src_node_id")}


def _bridge_lemma_src_set(
    lemmas: list[dict[str, Any]],
    *,
    sample_id: str | None = None,
    pair_index: int | None = None,
) -> set[str]:
    out: set[str] = set()
    for x in lemmas:
        if x.get("edge_type") != "INTER_HOP_BRIDGE_CONTAIN":
            continue
        src = str(x.get("src_node_id") or "")
        if not src:
            continue
        if sample_id is not None and str(x.get("sample_id") or "") != sample_id:
            continue
        if pair_index is not None and x.get("pair_index") != pair_index:
            continue
        out.add(src)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def eval_narrative_lemma_sample(
    sample: dict[str, Any],
    *,
    lemma_index: dict[str, list[dict[str, Any]]],
    bidirectional: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    path = list(sample.get("path") or [])
    hop_rows: list[dict[str, Any]] = []
    for hop in path:
        verse_ref = _canon_verse(str(hop.get("verse_ref") or ""))
        lemmas = lemma_index.get(verse_ref, [])
        atoms = bidirectional.get(verse_ref, [])
        has_proxy = any(str(e.get("edge_type") or "") == "BI_ATOM_PROXY_CONTAIN" for e in lemmas)
        hop_rows.append(
            {
                "hop": hop.get("hop"),
                "anchor_id": hop.get("anchor_id"),
                "verse_ref": verse_ref,
                "lemma_edge_count": len(lemmas),
                "lemma_edge_hit": len(lemmas) > 0,
                "bidirectional_atom_count": len(atoms),
                "bidirectional_atom_hit": len(atoms) > 0 or has_proxy,
                "bidirectional_atom_proxy_hit": has_proxy,
            }
        )

    inter_hop: list[dict[str, Any]] = []
    sample_id = str(sample.get("sample_id") or "")
    for i in range(len(hop_rows) - 1):
        vr_a = hop_rows[i]["verse_ref"]
        vr_b = hop_rows[i + 1]["verse_ref"]
        atoms_a = _atom_id_set(bidirectional.get(vr_a, []))
        atoms_b = _atom_id_set(bidirectional.get(vr_b, []))
        lemmas_a = _lemma_src_set(lemma_index.get(vr_a, []))
        lemmas_b = _lemma_src_set(lemma_index.get(vr_b, []))
        bridge_a = _bridge_lemma_src_set(
            lemma_index.get(vr_a, []), sample_id=sample_id, pair_index=i
        )
        bridge_b = _bridge_lemma_src_set(
            lemma_index.get(vr_b, []), sample_id=sample_id, pair_index=i
        )
        shared_atoms = sorted(atoms_a & atoms_b)
        shared_lemmas = sorted(lemmas_a & lemmas_b)
        shared_bridge_lemmas = sorted(bridge_a & bridge_b)
        inter_hop.append(
            {
                "from_hop": i,
                "to_hop": i + 1,
                "verse_refs": [vr_a, vr_b],
                "atom_jaccard": round(jaccard(atoms_a, atoms_b), 4),
                "lemma_jaccard": round(jaccard(lemmas_a, lemmas_b), 4),
                "bridge_lemma_jaccard": round(jaccard(bridge_a, bridge_b), 4),
                "shared_atom_count": len(shared_atoms),
                "shared_lemma_count": len(shared_lemmas),
                "shared_bridge_lemma_count": len(shared_bridge_lemmas),
                "curated_bridge_pair": len(shared_bridge_lemmas) > 0,
                "shared_atoms_sample": shared_atoms[:8],
                "shared_lemmas_sample": shared_lemmas[:8],
                "shared_bridge_lemmas_sample": shared_bridge_lemmas[:8],
            }
        )

    hop_count = len(hop_rows)
    lemma_hits = sum(1 for h in hop_rows if h["lemma_edge_hit"])
    bi_hits = sum(1 for h in hop_rows if h["bidirectional_atom_hit"])
    pair_count = len(inter_hop)
    mean_atom_j = (
        sum(p["atom_jaccard"] for p in inter_hop) / pair_count if pair_count else None
    )
    mean_lemma_j = (
        sum(p["lemma_jaccard"] for p in inter_hop) / pair_count if pair_count else None
    )
    mean_bridge_lemma_j = (
        sum(p["bridge_lemma_jaccard"] for p in inter_hop) / pair_count if pair_count else None
    )

    return {
        "sample_id": sample.get("sample_id"),
        "hop_count": hop_count,
        "lemma_edge_hop_hits": lemma_hits,
        "bidirectional_atom_hop_hits": bi_hits,
        "path_lemma_edge_coverage": lemma_hits > 0,
        "path_full_bidirectional_coverage": bi_hits == hop_count and hop_count > 0,
        "mean_inter_hop_atom_jaccard": round(mean_atom_j, 4) if mean_atom_j is not None else None,
        "mean_inter_hop_lemma_jaccard": round(mean_lemma_j, 4) if mean_lemma_j is not None else None,
        "mean_inter_hop_bridge_lemma_jaccard": round(mean_bridge_lemma_j, 4)
        if mean_bridge_lemma_j is not None
        else None,
        "hops": hop_rows,
        "inter_hop": inter_hop,
    }


def build_narrative_lemma_overlap_report(
    bridge: dict[str, Any] | None = None,
    *,
    lemma_index: dict[str, list[dict[str, Any]]] | None = None,
    bidirectional: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    bridge = bridge or json.loads(BRIDGE.read_text(encoding="utf-8"))
    lemma_index = lemma_index if lemma_index is not None else load_lemma_verse_index()
    bidirectional = bidirectional if bidirectional is not None else load_bidirectional_atoms()

    samples = list(bridge.get("narrative_path_samples") or [])
    rows = [
        eval_narrative_lemma_sample(s, lemma_index=lemma_index, bidirectional=bidirectional)
        for s in samples
    ]

    total_hops = sum(r["hop_count"] for r in rows)
    lemma_hop_hits = sum(r["lemma_edge_hop_hits"] for r in rows)
    bi_hop_hits = sum(r["bidirectional_atom_hop_hits"] for r in rows)
    path_lemma_cov = sum(1 for r in rows if r["path_lemma_edge_coverage"])
    path_bi_full = sum(1 for r in rows if r["path_full_bidirectional_coverage"])
    pair_rows = [p for r in rows for p in r["inter_hop"]]
    atom_j_values = [p["atom_jaccard"] for p in pair_rows]
    lemma_j_values = [p["lemma_jaccard"] for p in pair_rows]
    bridge_lemma_j_values = [p["bridge_lemma_jaccard"] for p in pair_rows]
    curated_bridge_pair_count = sum(1 for p in pair_rows if p.get("curated_bridge_pair"))

    lexicon_rows = None
    if LEXICON.is_file():
        try:
            lex = json.loads(LEXICON.read_text(encoding="utf-8"))
            if isinstance(lex, list):
                lexicon_rows = len(lex)
            elif isinstance(lex, dict):
                lexicon_rows = lex.get("row_count") or len(lex.get("rows") or [])
        except json.JSONDecodeError:
            lexicon_rows = None

    n = len(rows)
    return {
        "schema": "logos_narrative_lemma_overlap_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "note_ko": (
            "B-track: 8 narrative paths × sparse lemma edges + 41k bidirectional atom index. "
            "NOT Track A alignment_pass_rate; NOT 41k bulk OrbGraphBloom fusion."
        ),
        "inputs": {
            "lemma_edges_jsonl": str(LEMMA_EDGES.relative_to(ROOT)).replace("\\", "/"),
            "bidirectional_index": str(BIDIRECTIONAL.relative_to(ROOT)).replace("\\", "/"),
            "lexicon_41658": str(LEXICON.relative_to(ROOT)).replace("\\", "/"),
            "lexicon_row_count": lexicon_rows,
            "lemma_index_verse_count": len(lemma_index),
            "bidirectional_verse_count": len(bidirectional),
        },
        "narrative_sample_count": n,
        "summary": {
            "hop_lemma_edge_hit_rate": round(lemma_hop_hits / total_hops, 4) if total_hops else 0.0,
            "hop_bidirectional_atom_hit_rate": round(bi_hop_hits / total_hops, 4) if total_hops else 0.0,
            "path_lemma_edge_coverage_rate": round(path_lemma_cov / n, 4) if n else 0.0,
            "path_full_bidirectional_coverage_rate": round(path_bi_full / n, 4) if n else 0.0,
            "mean_inter_hop_atom_jaccard": round(sum(atom_j_values) / len(atom_j_values), 4)
            if atom_j_values
            else None,
            "mean_inter_hop_lemma_jaccard": round(sum(lemma_j_values) / len(lemma_j_values), 4)
            if lemma_j_values
            else None,
            "mean_inter_hop_bridge_lemma_jaccard": round(
                sum(bridge_lemma_j_values) / len(bridge_lemma_j_values), 4
            )
            if bridge_lemma_j_values
            else None,
            "curated_bridge_pair_rate": round(curated_bridge_pair_count / len(pair_rows), 4)
            if pair_rows
            else 0.0,
            "curated_bridge_pair_count": curated_bridge_pair_count,
            "total_hops": total_hops,
            "lemma_edge_hop_hits": lemma_hop_hits,
            "bidirectional_atom_hop_hits": bi_hop_hits,
            "path_lemma_edge_coverage_count": path_lemma_cov,
            "path_full_bidirectional_coverage_count": path_bi_full,
            "inter_hop_pair_count": len(pair_rows),
        },
        "samples": rows,
        "reproducible_command": "py scripts/run_logos_narrative_lemma_overlap_eval_chain_v1.py",
    }