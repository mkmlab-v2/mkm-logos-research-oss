#!/usr/bin/env python3
"""Pet companion subgraph router — observation bridges + token overlap ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_REGISTRY = ART / "pet_companion_observation_bridge_registry_v1_latest.json"
DEFAULT_SLICE = ART / "pet_companion_local_graph_slice_v1_latest.json"
DEFAULT_OUT = ART / "pet_companion_subgraph_router_v1_latest.json"

SCHEMA = "pet_companion_subgraph_router_v1"
VERSION = "1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_common():
    path = ROOT / "scripts/mkm_graph_subgraph_router_common_v1.py"
    spec = importlib.util.spec_from_file_location("mkm_graph_subgraph_router_common_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _observation_ids_from_bridge(bridge: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for node in bridge.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "observation_ref":
            continue
        oid = node.get("observation_id") or node.get("node_id", "")
        if isinstance(oid, str) and oid and oid not in seen:
            seen.add(oid)
            out.append(oid)
    return out


def route(
    query: str,
    *,
    registry: dict[str, Any],
    graph_slice: dict[str, Any] | None,
    top_bridges: int,
    common: Any,
) -> dict[str, Any]:
    query_tokens = common.tokenize(query)
    bridge_docs: list[tuple[int, dict[str, Any], str]] = []
    for entry in registry.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        path = ROOT / rel
        doc = _load_json(path)
        if not doc:
            continue
        score = common.score_bridge(query_tokens, doc)
        if score > 0:
            bridge_docs.append((score, doc, rel))

    bridge_docs.sort(key=lambda x: x[0], reverse=True)
    selected = bridge_docs[:top_bridges]

    paths_out: list[dict[str, Any]] = []
    observation_ids: list[str] = []
    seen_o: set[str] = set()
    for score, doc, rel in selected:
        for path in doc.get("paths") or []:
            if not isinstance(path, dict):
                continue
            paths_out.append(
                {
                    "bridge_artifact": rel,
                    "path_id": path.get("path_id"),
                    "steps": path.get("steps"),
                    "note_ko": path.get("note_ko"),
                    "match_score": score,
                }
            )
        for oid in _observation_ids_from_bridge(doc):
            if oid not in seen_o:
                seen_o.add(oid)
                observation_ids.append(oid)

    slice_nodes = 0
    slice_edges = 0
    if graph_slice:
        slice_nodes = int(graph_slice.get("node_count") or 0)
        slice_edges = int(graph_slice.get("edge_count") or 0)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": query,
        "query_tokens": query_tokens,
        "bridges_matched": len(selected),
        "paths": paths_out,
        "observation_ids": observation_ids,
        "local_graph_slice": {"node_count": slice_nodes, "edge_count": slice_edges},
        "policy": {
            "no_veterinary_diagnosis_claim": True,
            "track_wall": "B_track_pet_b2c_not_track_A",
            "router_kind": "token_overlap_pet_observation_subgraph_v1",
            "must_not_merge_with": ["logos_bible_subgraph", "mkm_ops_memory_graph"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", type=str, default="")
    ap.add_argument("--scenario-id", type=str, default="", help="e.g. walk_demo_01")
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--graph-slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top-bridges", type=int, default=2)
    args = ap.parse_args()

    query = (args.query or "").strip()
    if not query:
        defaults = {
            "walk_demo_01": "산책 패턴이 계속 반복돼요",
            "health_demo_01": "우리 아이가 산책 후 다리를 조금 불편해해요",
            "safety_demo_01": "응급 증상이 의심돼요 병원",
        }
        query = defaults.get(args.scenario_id.strip(), "반려 동물 건강 체크리스트")

    reg_path = args.registry_json if args.registry_json.is_absolute() else ROOT / args.registry_json
    slice_path = args.graph_slice_json if args.graph_slice_json.is_absolute() else ROOT / args.graph_slice_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    registry = _load_json(reg_path)
    if not registry:
        print(json.dumps({"ok": False, "error": "missing registry"}, ensure_ascii=False))
        return 2

    common = _load_common()
    doc = route(
        query,
        registry=registry,
        graph_slice=_load_json(slice_path),
        top_bridges=max(1, args.top_bridges),
        common=common,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "bridges_matched": doc["bridges_matched"],
                "paths": len(doc["paths"]),
                "observation_ids": len(doc["observation_ids"]),
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
