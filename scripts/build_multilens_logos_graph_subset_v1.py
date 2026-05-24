#!/usr/bin/env python3
"""Build fixed Logos+Graph-hit V2 bench subset (COMP-ATOM-05 / B-track)."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT = ROOT / "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json"
NODES = ROOT / "docs/final/artifacts/global_atom_network_nodes_latest.jsonl"
EDGES = ROOT / "docs/final/artifacts/global_atom_network_edges_latest.jsonl"
LOGOS_RE = re.compile(r"성경|bible|logos", re.IGNORECASE)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_gr() -> Any:
    path = ROOT / "scripts" / "run_graphrag_pilot_router_v1.py"
    spec = importlib.util.spec_from_file_location("graphrag_pilot_router_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    if not INPUT_V2.is_file():
        print(json.dumps({"error": "missing V2 input"}, ensure_ascii=False))
        return 2

    full = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    graph_hit_ids: set[str] = set()
    if NODES.is_file() and EDGES.is_file():
        gr = _load_gr()
        nodes = gr._load_jsonl(NODES)
        edges = gr._load_jsonl(EDGES)
        node_map, adj = gr._build_graph(nodes, edges, min_similarity=0.9)
        for case in full.get("compression_cases") or []:
            cid = str(case.get("id", ""))
            raw = str(case.get("raw_text", ""))
            kws = gr._keywords(raw)
            seeds = gr._seed_nodes(list(node_map.values()), kws, topk=8)
            seed_ids = [n["node_id"] for n in seeds if n.get("node_id")]
            expanded, _ = gr._multi_hop_expand(
                seed_ids=seed_ids, adj=adj, max_hops=2, max_edges=80
            )
            if expanded:
                graph_hit_ids.add(cid)

    comp: list[dict[str, Any]] = []
    for c in full.get("compression_cases") or []:
        cid = str(c.get("id", ""))
        if LOGOS_RE.search(str(c.get("raw_text", ""))) or cid in graph_hit_ids:
            comp.append(c)

    fus: list[dict[str, Any]] = []
    for c in full.get("fusion_answer_cases") or []:
        if "bible" in (c.get("required_axes") or []):
            fus.append(c)

    doc = {
        "schema": "multilens_performance_eval_input_logos_graph_subset_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "parent_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "subset_definition": (
            "compression: 성경|bible|logos in raw OR atom-network expansion; "
            "fusion: required_axes includes bible"
        ),
        "compression_cases": comp,
        "fusion_answer_cases": fus,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "compression_cases": len(comp),
                "fusion_answer_cases": len(fus),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
