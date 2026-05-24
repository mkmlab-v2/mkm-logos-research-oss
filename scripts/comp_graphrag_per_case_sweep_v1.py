#!/usr/bin/env python3
"""B-track: per-case GraphRAG anchor must_keep (micro-eval aggregate, research only)."""

from __future__ import annotations

import importlib.util
import json
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
    _load_gr,
    _metrics,
    _route_case,
    _utc,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

OUT = PILOT / "comp_graphrag_per_case_sweep_v1.json"
MAX_CASE_ANCHORS = 12


def _aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        return {}
    n = len(reports)
    saving = 0.0
    jacc = 0.0
    min_j = 1.0
    sens_ok = True
    for r in reports:
        cm = r.get("compression_metrics") or {}
        saving += float(cm.get("global_token_saving_rate", 0.0))
        j = float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0))
        jacc += j
        min_j = min(min_j, float(cm.get("min_reconstruction_fidelity_jaccard", 1.0)))
        qg = r.get("quality_gate") or {}
        sens_ok = sens_ok and bool(qg.get("sensitive_integrity_ok"))
    return {
        "cases_evaluated": n,
        "global_token_saving_rate": saving / n,
        "avg_reconstruction_fidelity_jaccard": jacc / n,
        "min_reconstruction_fidelity_jaccard": min_j,
        "sensitive_integrity_ok": sens_ok,
    }


def _eval_cases(
    cases: list[dict[str, Any]],
    *,
    per_case_mk: bool,
    case_routes: dict[str, dict[str, Any]],
    bridge: bool,
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    reports: list[dict[str, Any]] = []
    for case in cases:
        cid = str(case.get("id", ""))
        mk = set(BASE_MUST_KEEP)
        if per_case_mk:
            route = case_routes.get(cid) or {}
            for t in (route.get("anchor_terms") or [])[:MAX_CASE_ANCHORS]:
                if len(t) >= 3:
                    mk.add(t)
        sub = {"compression_cases": [case], "fusion_answer_cases": []}
        reports.append(
            evaluate_report(
                sub,
                must_keep=mk,
                apply_gematria_4d_bridge_policy=bridge,
                emit_semantic_pointer=True,
                **kw,
            )
        )
    return _aggregate(reports)


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

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    case_routes: dict[str, dict[str, Any]] = {}
    graph_hit_ids: list[str] = []
    for case in cases:
        cid = str(case.get("id", ""))
        route = _route_case(gr, text=str(case.get("raw_text", "")), node_map=node_map, adj=adj)
        route["case_id"] = cid
        case_routes[cid] = route
        if int(route.get("expanded_node_count") or 0) > 0:
            graph_hit_ids.append(cid)

    global_baseline = _eval_cases(cases, per_case_mk=False, case_routes=case_routes, bridge=False)
    global_union = _eval_cases(cases, per_case_mk=True, case_routes=case_routes, bridge=False)
    hit_cases = [c for c in cases if str(c.get("id")) in graph_hit_ids]
    hit_per_case = _eval_cases(hit_cases, per_case_mk=True, case_routes=case_routes, bridge=False)
    hit_bridge = _eval_cases(hit_cases, per_case_mk=True, case_routes=case_routes, bridge=True)

    doc = {
        "schema": "comp_graphrag_per_case_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "active_report_untouched": True,
        "gate_status": status,
        "graph_hit_case_ids": graph_hit_ids,
        "modes": {
            "global_baseline_must_keep": global_baseline,
            "global_per_case_graph_anchors": global_union,
            "graph_hit_only_per_case": hit_per_case,
            "graph_hit_per_case_bridge_on": hit_bridge,
        },
        "deltas_per_case_vs_global_baseline": {
            k: round(global_union[k] - global_baseline[k], 6)
            for k in ("global_token_saving_rate", "avg_reconstruction_fidelity_jaccard")
            if isinstance(global_union.get(k), (int, float))
        },
        "note": (
            "Per-case micro-eval: each compression case evaluated alone then averaged. "
            "Differs from batch evaluate_report on full V2 doc."
        ),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "graph_hits": len(graph_hit_ids),
                "deltas": doc["deltas_per_case_vs_global_baseline"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
