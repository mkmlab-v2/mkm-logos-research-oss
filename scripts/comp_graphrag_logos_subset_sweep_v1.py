#!/usr/bin/env python3
"""B-track: Logos/Bible-tagged V2 subset — GraphRAG must_keep vs baseline (research only)."""

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

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: E402
    BASE_MUST_KEEP,
    GATE,
    INPUT_V2,
    NODES,
    EDGES,
    PILOT,
    _base_eval_kwargs,
    _build_graph_must_keep,
    _eval_combo,
    _load_gr,
    _metrics,
    _route_case,
    _utc,
)

OUT = PILOT / "comp_graphrag_logos_subset_sweep_v1.json"
LOGOS_RE = re.compile(r"성경|bible|logos", re.IGNORECASE)


def _logos_subset(src: dict[str, Any], case_routes: list[dict[str, Any]]) -> dict[str, Any]:
    route_by_id = {r["case_id"]: r for r in case_routes}
    comp: list[dict[str, Any]] = []
    for c in src.get("compression_cases") or []:
        cid = str(c.get("id", ""))
        raw = str(c.get("raw_text", ""))
        route = route_by_id.get(cid) or {}
        graph_hit = int(route.get("expanded_node_count") or 0) > 0
        if LOGOS_RE.search(raw) or graph_hit:
            comp.append(c)
    fus: list[dict[str, Any]] = []
    for c in src.get("fusion_answer_cases") or []:
        axes = c.get("required_axes") or []
        if "bible" in axes:
            fus.append(c)
    return {
        "compression_cases": comp,
        "fusion_answer_cases": fus,
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    if not NODES.is_file() or not EDGES.is_file():
        print(json.dumps({"error": "missing atom network jsonl"}, ensure_ascii=False))
        return 2

    gate = json.loads(GATE.read_text(encoding="utf-8"))
    status = str(((gate.get("summary") or {}).get("status")) or "").upper()
    if status != "GO":
        print(json.dumps({"error": f"gate not GO: {status}"}, ensure_ascii=False))
        return 3

    gr = _load_gr()
    nodes = gr._load_jsonl(NODES)
    edges = gr._load_jsonl(EDGES)
    node_map, adj = gr._build_graph(nodes, edges, min_similarity=0.9)

    full = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    case_routes: list[dict[str, Any]] = []
    for case in full.get("compression_cases") or []:
        cid = str(case.get("id", ""))
        route = _route_case(gr, text=str(case.get("raw_text", "")), node_map=node_map, adj=adj)
        route["case_id"] = cid
        case_routes.append(route)

    subset = _logos_subset(full, case_routes)
    graph_mk = _build_graph_must_keep(case_routes)

    combos = [
        _eval_combo(subset, "logos_economy_baseline", BASE_MUST_KEEP, bridge=False),
        _eval_combo(subset, "logos_graphrag_must_keep", graph_mk, bridge=False),
        _eval_combo(
            subset,
            "logos_graphrag_selective_ssot",
            graph_mk,
            bridge=True,
            allowlist=frozenset({"ssot"}),
        ),
    ]

    b0, g0 = combos[0]["metrics"], combos[1]["metrics"]
    doc = {
        "schema": "comp_graphrag_logos_subset_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "active_report_untouched": True,
        "gate_status": status,
        "subset_definition": (
            "compression: raw matches 성경|bible|logos OR graph expansion>0; "
            "fusion: required_axes contains bible"
        ),
        "subset_counts": {
            "compression_cases": len(subset.get("compression_cases") or []),
            "fusion_answer_cases": len(subset.get("fusion_answer_cases") or []),
        },
        "subset_case_ids": [c.get("id") for c in subset.get("compression_cases") or []],
        "combos": combos,
        "deltas_graphrag_vs_baseline": {
            "global_token_saving_rate": round(
                g0["global_token_saving_rate"] - b0["global_token_saving_rate"], 6
            ),
            "avg_reconstruction_fidelity_jaccard": round(
                g0["avg_reconstruction_fidelity_jaccard"]
                - b0["avg_reconstruction_fidelity_jaccard"],
                6,
            ),
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "subset": doc["subset_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
