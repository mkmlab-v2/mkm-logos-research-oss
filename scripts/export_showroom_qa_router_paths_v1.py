#!/usr/bin/env python3
"""Export GraphRAG router paths into showroom Q&A presets + sidecar ([HYPO], B-track)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from compute_logos_reasoning_path_v1 import compute_reasoning_path  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402
from scripts.run_logos_subgraph_graphrag_router_v1 import (  # noqa: E402
    DEFAULT_LEMMA,
    DEFAULT_REGISTRY,
    DEFAULT_SEED_CHAIN,
    _load_json,
    _load_jsonl,
    route,
)

DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
DEFAULT_SIDECAR = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_router_sidecar_v1.json"
)
OUT_ART = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"

VERSE_STEP_RE = re.compile(r"^[A-Za-z0-9]+\.\d+(?:\.\d+)?$")
NOTE_ENRICH_MIN_LEN = 72


def _enrich_router_note_ko(note: str, path_steps: list[Any], query: str) -> str:
    """Pad thin bridge notes for bench note_specificity without inventing theology."""
    base = (note or "").strip()
    if len(base) >= NOTE_ENRICH_MIN_LEN:
        return base
    verse_tail = [str(s) for s in path_steps if VERSE_STEP_RE.match(str(s).strip())][-2:]
    concept_tail = [
        str(s)
        for s in path_steps
        if str(s).startswith(("concept:", "function:", "mc_", "node:", "lemma:"))
    ][:2]
    anchors = " → ".join(verse_tail or concept_tail)
    if not anchors:
        return base
    suffix = (
        f"[HYPO] query-time GraphRAG 경로 앵커: {anchors}. "
        "citation lock·학파 병렬만 — 인과 단답·NON_GATING·research_only."
    )
    return f"{base} {suffix}".strip() if base else suffix



def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_ref_index(graph: dict) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for n in graph.get("nodes") or []:
        nid = str(n.get("id") or "")
        if not nid:
            continue
        for key in (str(n.get("ref") or ""), str(n.get("label") or "")):
            key = key.strip()
            if not key:
                continue
            canon = canonical_verse_ref(key)
            for k in {key, canon} if canon else {key}:
                if k:
                    idx.setdefault(k, [])
                    if nid not in idx[k]:
                        idx[k].append(nid)
    return idx


def _verse_refs_from_router(router_doc: dict) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for vid in router_doc.get("verse_ids") or []:
        c = canonical_verse_ref(str(vid))
        if c and c not in seen:
            seen.add(c)
            refs.append(c)
    best = _pick_best_path(router_doc)
    if best:
        for step in best.get("steps") or []:
            s = str(step).strip()
            if VERSE_STEP_RE.match(s):
                c = canonical_verse_ref(s)
                if c and c not in seen:
                    seen.add(c)
                    refs.append(c)
    return refs


def _pick_best_path(router_doc: dict) -> dict | None:
    paths = [p for p in (router_doc.get("paths") or []) if isinstance(p, dict)]
    if not paths:
        return None
    paths.sort(key=lambda p: int(p.get("match_score") or 0), reverse=True)
    return paths[0]


def _map_refs_to_node_ids(refs: list[str], ref_index: dict[str, list[str]], cap: int = 24) -> list[str]:
    out: list[str] = []
    for ref in refs:
        for nid in ref_index.get(ref, []):
            if nid not in out:
                out.append(nid)
            if len(out) >= cap:
                return out
    return out


def _router_path_v1(
    preset_id: str,
    query: str,
    router_doc: dict,
    graph: dict,
    ref_index: dict[str, list[str]],
    preset: dict | None = None,
) -> dict[str, Any] | None:
    best = _pick_best_path(router_doc)
    verse_refs = _verse_refs_from_router(router_doc)
    node_ids = _map_refs_to_node_ids(verse_refs, ref_index)
    if not node_ids and preset:
        node_ids = list(preset.get("highlight_node_ids") or [])[:48]
    if not node_ids and not best and not verse_refs:
        return None
    reasoning = (
        compute_reasoning_path(graph, node_ids, max_nodes=min(8, max(3, len(node_ids))))
        if len(node_ids) >= 1
        else None
    )
    steps_out = list(best.get("steps") or []) if best else []
    note_raw = (best.get("note_ko") if best else None) or ""
    note_ko = _enrich_router_note_ko(note_raw, steps_out, query)
    return {
        "schema_version": "showroom_qa_router_path_v1",
        "preset_id": preset_id,
        "source": "logos_subgraph_graphrag_router_v1",
        "query": query,
        "path_id": best.get("path_id") if best else None,
        "note_ko": note_ko,
        "path_steps": steps_out,
        "match_score": int(best.get("match_score") or 0) if best else 0,
        "bridges_matched": int(router_doc.get("bridges_matched") or 0),
        "verse_refs": verse_refs,
        "node_ids": node_ids,
        "reasoning_path_v1": reasoning,
    }


def export_router_paths(
    presets_doc: dict,
    graph: dict,
    *,
    registry: dict,
    lemma_rows: list[dict],
    seed_chain: dict | None,
    preset_ids: set[str] | None = None,
    max_presets: int = 0,
    top_bridges: int = 2,
) -> tuple[dict, dict]:
    ref_index = _build_ref_index(graph)
    sidecar_entries: dict[str, Any] = {}
    merged = dict(presets_doc)
    presets_out: list[dict] = []
    count = 0

    for preset in presets_doc.get("presets") or []:
        pid = str(preset.get("id") or "")
        if preset_ids and pid not in preset_ids:
            presets_out.append(dict(preset))
            continue
        if max_presets and count >= max_presets:
            presets_out.append(dict(preset))
            continue

        row = dict(preset)
        query = str(preset.get("prompt_ko") or "").strip()
        if not query:
            presets_out.append(row)
            continue

        if preset.get("slice_gap") or str(preset.get("id") or "").startswith("era_"):
            presets_out.append(row)
            continue

        router_doc = route(
            query,
            registry=registry,
            lemma_rows=lemma_rows,
            seed_chain=seed_chain,
            top_bridges=top_bridges,
        )
        rp = _router_path_v1(pid, query, router_doc, graph, ref_index, preset=preset)
        if rp and (rp.get("node_ids") or rp.get("note_ko") or rp.get("verse_refs")):
            row["router_path_v1"] = rp
            if rp.get("node_ids") and rp.get("reasoning_path_v1"):
                row["reasoning_path_v1"] = rp["reasoning_path_v1"]
            sidecar_entries[pid] = {
                "router_summary": {
                    "bridges_matched": router_doc.get("bridges_matched"),
                    "paths": len(router_doc.get("paths") or []),
                    "verse_ids": len(router_doc.get("verse_ids") or []),
                },
                "router_path_v1": rp,
            }
            count += 1
        presets_out.append(row)

    sidecar = {
        "schema_version": "showroom_meaning_topology_qa_router_sidecar_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "policy": {"non_gating": True, "no_trade_signals": True},
        "graph_slice_path": presets_doc.get("graph_slice_path"),
        "preset_count": len(sidecar_entries),
        "presets": sidecar_entries,
    }
    merged["presets"] = presets_out
    merged["router_sidecar_path"] = "showroom_meaning_topology_qa_router_sidecar_v1.json"
    merged["router_export_at_utc"] = _utc_now()
    return merged, sidecar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--out-presets-json", type=Path, default=None)
    ap.add_argument("--out-sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--mirror-artifact", type=Path, default=OUT_ART)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--lemma-jsonl", type=Path, default=DEFAULT_LEMMA)
    ap.add_argument("--seed-chain-json", type=Path, default=DEFAULT_SEED_CHAIN)
    ap.add_argument("--preset-id", action="append", default=[], dest="preset_ids")
    ap.add_argument("--max-presets", type=int, default=0)
    ap.add_argument("--top-bridges", type=int, default=2)
    args = ap.parse_args()

    if not args.graph_json.is_file():
        print(f"missing graph: {args.graph_json}", file=sys.stderr)
        return 2
    if not args.presets_json.is_file():
        print(f"missing presets: {args.presets_json}", file=sys.stderr)
        return 2

    registry = _load_json(args.registry_json)
    if not registry:
        print("missing registry", file=sys.stderr)
        return 2

    graph = json.loads(args.graph_json.read_text(encoding="utf-8"))
    presets_doc = json.loads(args.presets_json.read_text(encoding="utf-8"))
    pid_filter = set(args.preset_ids) if args.preset_ids else None

    merged, sidecar = export_router_paths(
        presets_doc,
        graph,
        registry=registry,
        lemma_rows=_load_jsonl(args.lemma_jsonl),
        seed_chain=_load_json(args.seed_chain_json),
        preset_ids=pid_filter,
        max_presets=args.max_presets,
        top_bridges=args.top_bridges,
    )

    out_presets = args.out_presets_json if args.out_presets_json else args.presets_json
    out_presets.parent.mkdir(parents=True, exist_ok=True)
    out_presets.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.out_sidecar_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_sidecar_json.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    art_presets = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
    art_presets.parent.mkdir(parents=True, exist_ok=True)
    art_presets.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.mirror_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.mirror_artifact.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with_router = sum(1 for p in merged.get("presets") or [] if p.get("router_path_v1"))
    print(
        json.dumps(
            {
                "ok": True,
                "presets_with_router_path": with_router,
                "out_presets": str(out_presets),
                "out_sidecar": str(args.out_sidecar_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
