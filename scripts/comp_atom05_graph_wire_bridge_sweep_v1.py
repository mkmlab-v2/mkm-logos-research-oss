#!/usr/bin/env python3
"""COMP-ATOM-05: Graph wire influence + selective per-case bridge (B-track sweep)."""

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
    NODES,
    EDGES,
    PILOT,
    _base_eval_kwargs,
    _load_gr,
    _metrics,
    _route_case,
    _utc,
)
from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
    build_case_graph_wire_influence_map,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

OUT = PILOT / "comp_atom05_graph_wire_bridge_sweep_v1.json"
SUBSET = ROOT / "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json"
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"


def _wire_atom_ids() -> list[str]:
    if not POC.is_file():
        return []
    doc = json.loads(POC.read_text(encoding="utf-8"))
    gr = doc.get("graph_rag") or {}
    ids: list[str] = []
    for nid in gr.get("reasoning_path_node_ids") or []:
        ids.append(str(nid))
    return ids


def _eval(
    src: dict[str, Any],
    combo_id: str,
    *,
    bridge_global: bool,
    graph_wire_selective: bool,
    influence: dict[str, dict[str, Any]],
    emit_sp: bool,
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        apply_gematria_4d_bridge_policy=bridge_global,
        bridge_policy_domain_allowlist=frozenset({"ssot"}) if bridge_global else None,
        graph_wire_selective_bridge=graph_wire_selective,
        case_graph_wire_influence=influence,
        emit_semantic_pointer=emit_sp,
        **kw,
    )
    sp_rows = [
        r
        for r in (report.get("compression_metrics") or {}).get("cases", [])
        if isinstance(r.get("semantic_pointer"), dict)
        and r["semantic_pointer"].get("graph_wire_influence_v1")
    ]
    return {
        "combo_id": combo_id,
        "metrics": _metrics(report),
        "semantic_pointer_with_wire_count": len(sp_rows),
        "bridge_boost_cases": sum(
            1 for v in influence.values() if v.get("bridge_boost")
        ),
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    if not SUBSET.is_file():
        print(json.dumps({"error": "run build_multilens_logos_graph_subset_v1.py first"}, ensure_ascii=False))
        return 2
    if not NODES.is_file() or not EDGES.is_file():
        print(json.dumps({"error": "missing atom network"}, ensure_ascii=False))
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

    src = json.loads(SUBSET.read_text(encoding="utf-8"))
    case_routes: list[dict[str, Any]] = []
    for case in src.get("compression_cases") or []:
        cid = str(case.get("id", ""))
        route = _route_case(gr, text=str(case.get("raw_text", "")), node_map=node_map, adj=adj)
        route["case_id"] = cid
        case_routes.append(route)

    influence = build_case_graph_wire_influence_map(
        case_routes, wire_atom_ids=_wire_atom_ids()
    )

    combos = [
        _eval(
            src,
            "atom05_baseline",
            bridge_global=False,
            graph_wire_selective=False,
            influence={},
            emit_sp=False,
        ),
        _eval(
            src,
            "atom05_wire_pointer_only",
            bridge_global=False,
            graph_wire_selective=False,
            influence=influence,
            emit_sp=True,
        ),
        _eval(
            src,
            "atom05_wire_selective_bridge",
            bridge_global=False,
            graph_wire_selective=True,
            influence=influence,
            emit_sp=True,
        ),
        _eval(
            src,
            "atom05_ssot_bridge_allowlist",
            bridge_global=True,
            graph_wire_selective=False,
            influence=influence,
            emit_sp=True,
        ),
    ]

    b0 = combos[0]["metrics"]
    w2 = combos[2]["metrics"]
    doc = {
        "schema": "comp_atom05_graph_wire_bridge_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_comp_atom05",
        "active_report_untouched": True,
        "gate_status": status,
        "input_subset": str(SUBSET.relative_to(ROOT)).replace("\\", "/"),
        "influence_case_count": len(influence),
        "bridge_boost_case_count": sum(1 for v in influence.values() if v.get("bridge_boost")),
        "combos": combos,
        "deltas_wire_selective_vs_baseline": {
            k: round(w2[k] - b0[k], 6)
            for k in ("global_token_saving_rate", "avg_reconstruction_fidelity_jaccard")
            if isinstance(b0.get(k), (int, float))
        },
        "compare_prior": "reports/constitution/btrack_pilot/comp_graphrag_logos_subset_sweep_v1.json",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "deltas": doc["deltas_wire_selective_vs_baseline"],
                "combos": {c["combo_id"]: c["metrics"] for c in combos},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
