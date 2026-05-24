#!/usr/bin/env python3
"""B-track: Logos wire PoC terms + semantic_pointer on logos/graph-hit subset."""

from __future__ import annotations

import json
import re
import subprocess
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
from scripts.comp_graphrag_logos_subset_sweep_v1 import _logos_subset  # noqa: E402

OUT = PILOT / "comp_graphrag_wire_semantic_sweep_v1.json"
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
PROFILE = ROOT / "docs/final/artifacts/logos_graph_wire_profile_v1_latest.json"


def _wire_must_keep_terms() -> set[str]:
    terms: set[str] = set()
    for path in (POC, PROFILE):
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        gr = doc.get("graph_rag") or {}
        for nid in gr.get("reasoning_path_node_ids") or gr.get("verse_node_ids") or []:
            s = str(nid)
            for part in re.split(r"[:.]+", s):
                p = part.lower()
                if len(p) >= 3 and p.isascii():
                    terms.add(p)
            if "aramaic" in s.lower():
                terms.add("aramaic")
    return terms


def _ensure_wire_artifacts() -> dict[str, Any]:
    if POC.is_file() and PROFILE.is_file():
        return {"refreshed": False, "steps": []}
    cmd = [sys.executable, str(ROOT / "scripts/build_logos_graph_wire_profile_v1.py")]
    proc = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    return {
        "refreshed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    wire_refresh = _ensure_wire_artifacts()
    wire_terms = _wire_must_keep_terms()

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
    wire_mk = graph_mk | wire_terms

    kw = _base_eval_kwargs()
    from scripts.report_multilens_performance_eval import evaluate_report  # noqa: WPS433

    report_sp = evaluate_report(
        subset,
        must_keep=wire_mk,
        apply_gematria_4d_bridge_policy=False,
        emit_semantic_pointer=True,
        **kw,
    )

    combos = [
        _eval_combo(subset, "wire_subset_baseline", BASE_MUST_KEEP, bridge=False),
        _eval_combo(subset, "wire_subset_graph_wire_mk", wire_mk, bridge=False),
    ]

    doc = {
        "schema": "comp_graphrag_wire_semantic_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "active_report_untouched": True,
        "gate_status": status,
        "wire_artifact_refresh": wire_refresh,
        "wire_terms_added": sorted(wire_terms),
        "wire_must_keep_size": len(wire_mk),
        "subset_counts": {
            "compression_cases": len(subset.get("compression_cases") or []),
            "fusion_answer_cases": len(subset.get("fusion_answer_cases") or []),
        },
        "combos": combos,
        "semantic_pointer_batch": {
            "emit_semantic_pointer": True,
            "metrics": _metrics(report_sp),
            "pointer_cases": len(
                [
                    r
                    for r in (report_sp.get("compression_case_results") or [])
                    if r.get("semantic_pointer")
                ]
            ),
        },
        "data_fabric_poc": "scripts/build_mkm_graph_wire_rag_poc_v1.py",
        "boundary_ack": "Wire byte metrics are separate from compression Jaccard; atom_id_sequence not yet in evaluate_report API.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b0, w0 = combos[0]["metrics"], combos[1]["metrics"]
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "wire_terms": len(wire_terms),
                "deltas": {
                    "global_token_saving_rate": round(
                        w0["global_token_saving_rate"] - b0["global_token_saving_rate"], 6
                    ),
                    "avg_reconstruction_fidelity_jaccard": round(
                        w0["avg_reconstruction_fidelity_jaccard"]
                        - b0["avg_reconstruction_fidelity_jaccard"],
                        6,
                    ),
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
