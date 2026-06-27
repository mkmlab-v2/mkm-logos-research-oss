#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build capped bible_meaning_graph subgraph JSON for public showroom topology viz ([HYPO]/NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from build_logos_oracle_inference_graph_overlay_v1 import build_overlay  # noqa: E402
DEFAULT_CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_insight_candidates_latest.json"
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json"
)
DEFAULT_ARTIFACT_MIRROR = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_JOB_BUNDLE = ROOT / "docs/final/artifacts/showroom_job_topology_seed_bundle_v1_latest.json"
DEFAULT_ERA_BUNDLE = ROOT / "docs/final/artifacts/showroom_chronology_era_topology_seed_bundle_v1_latest.json"
DEFAULT_CHRONOLOGY = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "no_trade_signals": True,
    "note_ko": (
        "성경·로고스 의미 연결망의 연구용 부분 그래프입니다. 종교·신학적 진리·투자·임상·실매매(Track A) "
        "근거가 아니며 운영 게이트·주문 트리거와 무관합니다."
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _node_kind(raw: dict[str, Any]) -> str:
    kind = str(raw.get("kind") or "").lower()
    if kind in ("theme", "regime"):
        return kind
    if raw.get("ref") or raw.get("corpus"):
        return "verse"
    return "other"


def _node_label(raw: dict[str, Any]) -> str:
    if raw.get("label"):
        return str(raw["label"])
    if raw.get("ref"):
        return str(raw["ref"])
    node_id = str(raw.get("node_id", ""))
    if "::" in node_id:
        return node_id.split("::", 1)[1]
    return node_id


def _load_nodes_index(path: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in _iter_jsonl(path):
        node_id = row.get("node_id")
        if node_id:
            index[str(node_id)] = row
    return index


def _pick_seeds(candidates_doc: dict[str, Any], seed_count: int) -> list[dict[str, Any]]:
    cands = list(candidates_doc.get("candidates") or [])
    cands.sort(key=lambda c: float(c.get("hub_score") or 0), reverse=True)
    return cands[:seed_count]


def _expand_subgraph(
    seed_ids: set[str],
    edges_path: Path,
    max_nodes: int,
    max_edges: int,
) -> tuple[set[str], list[dict[str, Any]]]:
    selected = set(seed_ids)
    pending_edges: list[dict[str, Any]] = []
    neighbor_score: dict[str, float] = defaultdict(float)

    for row in _iter_jsonl(edges_path):
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if not src or not dst:
            continue
        weight = float(row.get("weight") or 0.5)
        edge_type = str(row.get("edge_type") or "link")
        if src in selected or dst in selected:
            pending_edges.append(
                {
                    "src": src,
                    "dst": dst,
                    "edge_type": edge_type,
                    "weight": weight,
                }
            )
            other = dst if src in selected else src
            if other not in selected:
                neighbor_score[other] += weight

    while len(selected) < max_nodes:
        ranked_neighbors = sorted(neighbor_score.items(), key=lambda x: x[1], reverse=True)
        if not ranked_neighbors:
            break
        added = 0
        for node_id, _ in ranked_neighbors:
            if len(selected) >= max_nodes:
                break
            if node_id not in selected:
                selected.add(node_id)
                added += 1
        if added == 0:
            break
        neighbor_score = defaultdict(float)
        pending_edges = []
        for row in _iter_jsonl(edges_path):
            src = str(row.get("src_node_id") or "")
            dst = str(row.get("dst_node_id") or "")
            if not src or not dst:
                continue
            weight = float(row.get("weight") or 0.5)
            edge_type = str(row.get("edge_type") or "link")
            if src in selected or dst in selected:
                pending_edges.append(
                    {
                        "src": src,
                        "dst": dst,
                        "edge_type": edge_type,
                        "weight": weight,
                    }
                )
                other = dst if src in selected else src
                if other not in selected:
                    neighbor_score[other] += weight

    pending_edges.sort(key=lambda e: float(e["weight"]), reverse=True)
    edges_out: list[dict[str, Any]] = []
    seen_edge: set[tuple[str, str, str]] = set()
    for edge in pending_edges:
        if edge["src"] not in selected or edge["dst"] not in selected:
            continue
        key = (edge["src"], edge["dst"], edge["edge_type"])
        if key in seen_edge:
            continue
        seen_edge.add(key)
        edges_out.append(edge)
        if len(edges_out) >= max_edges:
            break

    return selected, edges_out


def _bundle_slice_nodes(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in bundle.get("nodes") or []:
        row: dict[str, Any] = {
            "id": n["id"],
            "label": n.get("label") or n["id"],
            "kind": n.get("kind") or "other",
        }
        if n.get("ref"):
            row["ref"] = n["ref"]
        if n.get("hub_score") is not None:
            row["hub_score"] = float(n["hub_score"])
        if n.get("stage_id"):
            row["stage_id"] = n["stage_id"]
        rows.append(row)
    return rows


def _merge_seed_bundle(
    doc: dict[str, Any],
    bundle: dict[str, Any],
    *,
    selection_key: str,
) -> dict[str, Any]:
    """Force-inject seed bundle nodes/edges into an existing slice document."""
    if not bundle:
        return doc
    node_by_id = {str(n["id"]): dict(n) for n in doc.get("nodes") or []}
    for row in _bundle_slice_nodes(bundle):
        node_by_id[row["id"]] = row

    edge_key = lambda e: (e["src"], e["dst"], e.get("edge_type") or "link")  # noqa: E731
    edges: list[dict[str, Any]] = list(doc.get("edges") or [])
    seen = {edge_key(e) for e in edges}
    for e in bundle.get("edges") or []:
        key = edge_key(e)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "src": e["src"],
                "dst": e["dst"],
                "edge_type": e.get("edge_type") or "link",
                "weight": float(e.get("weight") or 0.5),
            }
        )

    kind_counts: dict[str, int] = defaultdict(int)
    nodes_out = list(node_by_id.values())
    for n in nodes_out:
        kind_counts[str(n.get("kind") or "other")] += 1

    doc = dict(doc)
    doc["nodes"] = nodes_out
    doc["edges"] = edges
    stats = dict(doc.get("stats") or {})
    stats["node_count"] = len(nodes_out)
    stats["edge_count"] = len(edges)
    stats["kinds"] = dict(kind_counts)
    doc["stats"] = stats
    selection = dict(doc.get("selection") or {})
    forced = list(bundle.get("node_ids") or [])
    selection[selection_key] = {
        "schema": bundle.get("schema"),
        "forced_node_ids": forced,
        "verse_ref_count": bundle.get("verse_ref_count"),
        "era_count": bundle.get("era_count"),
        "stub_verse_count": bundle.get("stub_verse_count"),
    }
    selection["forced_node_ids"] = sorted(set(selection.get("forced_node_ids") or []) | set(forced))
    doc["selection"] = selection
    return doc


def _merge_job_bundle(
    doc: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Force-inject Job spine nodes/edges into an existing slice document."""
    if not bundle:
        return doc
    doc = _merge_seed_bundle(doc, bundle, selection_key="job_seed_bundle")
    selection = dict(doc.get("selection") or {})
    job_meta = dict(selection.get("job_seed_bundle") or {})
    job_meta.update(
        {
            "stage_count": bundle.get("stage_count"),
            "verse_ref_count": bundle.get("verse_ref_count"),
        }
    )
    selection["job_seed_bundle"] = job_meta
    doc["selection"] = selection
    return doc


def build_slice(
    *,
    candidates_path: Path,
    nodes_path: Path,
    edges_path: Path,
    seed_count: int,
    max_nodes: int,
    max_edges: int,
    job_bundle: dict[str, Any] | None = None,
    era_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not candidates_path.is_file():
        raise FileNotFoundError(f"candidates missing: {candidates_path}")
    if not nodes_path.is_file():
        raise FileNotFoundError(f"graph nodes missing: {nodes_path}")
    if not edges_path.is_file():
        raise FileNotFoundError(f"graph edges missing: {edges_path}")

    candidates_doc = _load_json(candidates_path)
    seeds = _pick_seeds(candidates_doc, seed_count)
    seed_ids = {str(c["source_node_id"]) for c in seeds if c.get("source_node_id")}
    if job_bundle:
        seed_ids.update(str(nid) for nid in (job_bundle.get("node_ids") or []))
    if era_bundle:
        seed_ids.update(str(nid) for nid in (era_bundle.get("node_ids") or []))
    hub_by_node = {str(c["source_node_id"]): float(c.get("hub_score") or 0) for c in seeds}
    cand_by_node = {str(c["source_node_id"]): str(c.get("candidate_id") or "") for c in seeds}

    reserved = 0
    if job_bundle:
        reserved += len(job_bundle.get("node_ids") or [])
    if era_bundle:
        reserved += len(era_bundle.get("node_ids") or [])
    expand_cap = max(max_nodes, reserved)
    selected_ids, edges = _expand_subgraph(seed_ids, edges_path, expand_cap, max_edges)
    if job_bundle:
        selected_ids.update(str(nid) for nid in (job_bundle.get("node_ids") or []))
    if era_bundle:
        selected_ids.update(str(nid) for nid in (era_bundle.get("node_ids") or []))
    nodes_index = _load_nodes_index(nodes_path)

    nodes_out: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = defaultdict(int)
    bundle_by_id: dict[str, dict[str, Any]] = {}
    for src in (job_bundle, era_bundle):
        if not src:
            continue
        for n in src.get("nodes") or []:
            bundle_by_id[str(n["id"])] = n
    for node_id in sorted(selected_ids):
        raw = nodes_index.get(node_id) or bundle_by_id.get(node_id)
        if not raw:
            continue
        if node_id in bundle_by_id and "kind" in bundle_by_id[node_id]:
            kind = str(bundle_by_id[node_id].get("kind") or "other")
            row = dict(bundle_by_id[node_id])
            row.setdefault("id", node_id)
            nodes_out.append(row)
            kind_counts[kind] += 1
            continue
        kind = _node_kind(raw)
        kind_counts[kind] += 1
        row = {
            "id": node_id,
            "label": _node_label(raw),
            "kind": kind,
        }
        if raw.get("corpus"):
            row["corpus"] = raw["corpus"]
        if raw.get("ref"):
            row["ref"] = raw["ref"]
        text_norm = str(raw.get("text_norm") or "").strip()
        if text_norm and kind == "verse":
            row["text_snippet_ko"] = text_norm[:160] + ("…" if len(text_norm) > 160 else "")
        if node_id in hub_by_node:
            row["hub_score"] = hub_by_node[node_id]
            row["candidate_id"] = cand_by_node.get(node_id)
        elif raw.get("hub_score") is not None:
            row["hub_score"] = float(raw["hub_score"])
        nodes_out.append(row)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    stale = now + timedelta(days=7)
    doc = {
        "schema_version": "showroom_meaning_topology_graph_slice_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stale_after_utc": stale.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "disclaimer": DISCLAIMER,
        "data_provenance": {
            "candidates_path": str(candidates_path.relative_to(ROOT)).replace("\\", "/"),
            "graph_nodes_path": str(nodes_path.relative_to(ROOT)).replace("\\", "/"),
            "graph_edges_path": str(edges_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "selection": {
            "seed_count": seed_count,
            "max_nodes": max_nodes,
            "max_edges": max_edges,
            "seed_candidate_ids": [str(c.get("candidate_id") or "") for c in seeds],
            "seed_source_node_ids": sorted(seed_ids),
        },
        "stats": {
            "node_count": len(nodes_out),
            "edge_count": len(edges),
            "kinds": dict(kind_counts),
        },
        "nodes": nodes_out,
        "edges": edges,
        "inference_overlay": build_overlay(root=ROOT),
    }
    if job_bundle:
        doc = _merge_job_bundle(doc, job_bundle)
    if era_bundle:
        doc = _merge_seed_bundle(doc, era_bundle, selection_key="chronology_era_seed_bundle")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build showroom meaning-topology graph slice JSON")
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--graph-nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--graph-edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--seed-count", type=int, default=14)
    ap.add_argument("--max-nodes", type=int, default=72)
    ap.add_argument("--max-edges", type=int, default=140)
    ap.add_argument("--job-seed-bundle", type=Path, default=None)
    ap.add_argument(
        "--include-job-spine",
        action="store_true",
        help=f"Load default Job seed bundle ({DEFAULT_JOB_BUNDLE.name})",
    )
    ap.add_argument("--era-seed-bundle", type=Path, default=None)
    ap.add_argument(
        "--include-chronology-era-spine",
        action="store_true",
        help=f"Load default chronology era seed bundle ({DEFAULT_ERA_BUNDLE.name})",
    )
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--mirror-artifact",
        type=Path,
        default=DEFAULT_ARTIFACT_MIRROR,
        help="Also write docs/final/artifacts/*_latest.json (default: on)",
    )
    ap.add_argument("--no-mirror-artifact", action="store_true")
    args = ap.parse_args()

    job_bundle = None
    bundle_path = args.job_seed_bundle
    if args.include_job_spine and bundle_path is None:
        bundle_path = DEFAULT_JOB_BUNDLE
    if bundle_path and bundle_path.is_file():
        job_bundle = _load_json(bundle_path)

    era_bundle = None
    era_path = args.era_seed_bundle
    if args.include_chronology_era_spine and era_path is None:
        era_path = DEFAULT_ERA_BUNDLE
    if era_path and era_path.is_file():
        era_bundle = _load_json(era_path)
    elif args.include_chronology_era_spine and args.chronology_json.is_file():
        from scripts.core.showroom_chronology_era_topology_seed_v1 import (  # noqa: E402
            build_chronology_era_seed_bundle,
        )

        chrono = _load_json(args.chronology_json)
        nodes_index = _load_nodes_index(args.graph_nodes_jsonl)
        edges_index = _iter_jsonl(args.graph_edges_jsonl)
        era_bundle = build_chronology_era_seed_bundle(
            chrono,
            nodes_index=nodes_index,
            edges_index=edges_index,
        )

    try:
        doc = build_slice(
            candidates_path=args.candidates_json,
            nodes_path=args.graph_nodes_jsonl,
            edges_path=args.graph_edges_jsonl,
            seed_count=args.seed_count,
            max_nodes=args.max_nodes,
            max_edges=args.max_edges,
            job_bundle=job_bundle,
            era_bundle=era_bundle,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(
        f"Wrote {args.out_json} nodes={doc['stats']['node_count']} "
        f"edges={doc['stats']['edge_count']}"
    )

    if not args.no_mirror_artifact and args.mirror_artifact:
        args.mirror_artifact.parent.mkdir(parents=True, exist_ok=True)
        args.mirror_artifact.write_text(text, encoding="utf-8")
        print(f"Mirrored {args.mirror_artifact}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
