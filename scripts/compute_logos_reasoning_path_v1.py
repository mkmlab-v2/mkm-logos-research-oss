#!/usr/bin/env python3
"""Derive logos_reasoning_path_v1 for showroom presets (deterministic, no LLM)."""
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KIND_RANK = {"theme": 0, "regime": 1, "era": 2, "verse": 3, "other": 9}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _adjacency(graph: dict) -> tuple[dict[str, list[str]], dict[tuple[str, str], dict]]:
    adj: dict[str, list[str]] = {}
    edge_map: dict[tuple[str, str], dict] = {}
    for e in graph.get("edges") or []:
        src, dst = str(e["src"]), str(e["dst"])
        adj.setdefault(src, []).append(dst)
        adj.setdefault(dst, []).append(src)
        edge_map[(src, dst)] = e
        edge_map[(dst, src)] = e
    return adj, edge_map


def _bfs_path(adj: dict[str, list[str]], start: str, goal: str, max_hops: int = 6) -> list[str] | None:
    if start == goal:
        return [start]
    q: deque[tuple[str, list[str]]] = deque([(start, [start])])
    seen = {start}
    while q:
        node, path = q.popleft()
        if len(path) > max_hops + 1:
            continue
        for nxt in adj.get(node, []):
            if nxt in seen:
                continue
            npath = path + [nxt]
            if nxt == goal:
                return npath
            seen.add(nxt)
            q.append((nxt, npath))
    return None


def _order_seeds(graph: dict, seed_ids: list[str], max_nodes: int = 5) -> list[str]:
    nodes = {str(n["id"]): n for n in graph.get("nodes") or []}
    uniq: list[str] = []
    for sid in seed_ids:
        if sid in nodes and sid not in uniq:
            uniq.append(sid)
    uniq.sort(
        key=lambda i: (
            KIND_RANK.get(str(nodes[i].get("kind") or "other"), 9),
            -float(nodes[i].get("hub_score") or 0),
            i,
        )
    )
    return uniq[:max_nodes]


def _path_edges(node_ids: list[str], edge_map: dict[tuple[str, str], dict]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for i in range(len(node_ids) - 1):
        a, b = node_ids[i], node_ids[i + 1]
        e = edge_map.get((a, b))
        if e:
            out.append({"src": a, "dst": b, "edge_type": str(e.get("edge_type") or "")})
    return out


def compute_reasoning_path(
    graph: dict,
    seed_ids: list[str],
    *,
    max_nodes: int = 5,
    max_hops: int = 6,
) -> dict[str, Any]:
    """Build a short linear reasoning path across the capped subgraph."""
    adj, edge_map = _adjacency(graph)
    ordered = _order_seeds(graph, seed_ids, max_nodes=max_nodes)
    if not ordered:
        return {
            "schema_version": "logos_reasoning_path_v1",
            "node_ids": [],
            "edges": [],
            "path_label_ko": "",
        }

    path: list[str] = [ordered[0]]
    for target in ordered[1:]:
        if target in path:
            continue
        segment = _bfs_path(adj, path[-1], target, max_hops=max_hops)
        if segment and len(segment) > 1:
            path.extend(segment[1:])
        elif target not in path:
            path.append(target)
        if len(path) >= max_nodes:
            break

    path = path[:max_nodes]
    edges = _path_edges(path, edge_map)
    labels: list[str] = []
    nodes = {str(n["id"]): n for n in graph.get("nodes") or []}
    for nid in path:
        n = nodes.get(nid, {})
        labels.append(str(n.get("label") or nid.split("::")[-1][:24]))

    return {
        "schema_version": "logos_reasoning_path_v1",
        "node_ids": path,
        "edges": edges,
        "path_label_ko": " → ".join(labels),
    }


def attach_paths_to_presets(presets_doc: dict, graph: dict) -> dict:
    out = dict(presets_doc)
    presets = []
    for p in presets_doc.get("presets") or []:
        row = dict(p)
        row.pop("router_path_v1", None)
        seeds = list(row.get("highlight_node_ids") or [])
        verse_seeds = [s for s in seeds if not str(s).startswith("era::")]
        era_seeds = [s for s in seeds if str(s).startswith("era::")]
        if row.get("slice_gap") and era_seeds:
            era_label = str(row.get("answer_title_ko") or row.get("prompt_ko") or "era hub")
            row["reasoning_path_v1"] = {
                "schema_version": "logos_reasoning_path_v1",
                "node_ids": era_seeds[:1],
                "edges": [],
                "path_label_ko": era_label.replace("연대기 · ", ""),
            }
        elif verse_seeds:
            path_seeds = list(dict.fromkeys(verse_seeds + era_seeds))
            row["reasoning_path_v1"] = compute_reasoning_path(
                graph, path_seeds, max_nodes=min(5, len(path_seeds))
            )
        elif len(seeds) >= 2:
            max_n = 3 if row.get("id") == "p3_theme_regime" else 5
            row["reasoning_path_v1"] = compute_reasoning_path(graph, seeds, max_nodes=max_n)
        presets.append(row)
    out["presets"] = presets
    fb = dict(presets_doc.get("fallback") or {})
    if fb.get("highlight_node_ids"):
        fb["reasoning_path_v1"] = compute_reasoning_path(
            graph, list(fb["highlight_node_ids"]), max_nodes=4
        )
    out["fallback"] = fb
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--graph-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
    )
    ap.add_argument(
        "--presets-json",
        type=Path,
        default=ROOT
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json",
    )
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--seed-ids", nargs="*", default=[])
    args = ap.parse_args()

    graph = _load(args.graph_json)
    if args.seed_ids:
        path = compute_reasoning_path(graph, list(args.seed_ids))
        print(json.dumps(path, ensure_ascii=False, indent=2))
        return 0

    presets_doc = _load(args.presets_json)
    merged = attach_paths_to_presets(presets_doc, graph)
    out = args.out_json if args.out_json is not None else args.presets_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "presets_with_path": sum(
                    1 for p in merged.get("presets") or [] if p.get("reasoning_path_v1")
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
