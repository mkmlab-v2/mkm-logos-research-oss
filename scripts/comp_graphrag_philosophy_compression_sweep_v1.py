#!/usr/bin/env python3
"""B-track: GraphRAG(atom network) anchors + philosophy compression combos.

Uses global_atom_network (CONSTITUTION §31.2a) to derive static anchor terms per bench case,
then runs 40-case V2 evaluate_report — never writes Track A active.

Writes: reports/constitution/btrack_pilot/comp_graphrag_philosophy_sweep_v1.json
"""
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

from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_graphrag_philosophy_sweep_v1.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
NODES = ROOT / "docs/final/artifacts/global_atom_network_nodes_latest.jsonl"
EDGES = ROOT / "docs/final/artifacts/global_atom_network_edges_latest.jsonl"
GATE = ROOT / "docs/final/artifacts/multi_symbol_gate_summary_latest.json"
POLICY_FLOOR = 0.47
TOP5 = frozenset({"cmp2_002", "cmp2_004", "cmp2_005", "cmp2_006", "cmp2_009"})
BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}
MAX_GRAPH_TERMS = 24

FORBIDDEN = frozenset(
    {
        (ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve(),
    }
)

_GR_MOD: Any = None


def _load_gr() -> Any:
    global _GR_MOD
    if _GR_MOD is not None:
        return _GR_MOD
    path = ROOT / "scripts" / "run_graphrag_pilot_router_v1.py"
    spec = importlib.util.spec_from_file_location("graphrag_pilot_router_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _GR_MOD = mod
    return mod


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _anchor_terms_from_nodes(nodes: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for n in nodes:
        for key in ("assigned_symbol", "regime_tag", "candidate_id"):
            v = n.get(key)
            if isinstance(v, str) and len(v) >= 2:
                for part in re.split(r"[_\s:]+", v.lower()):
                    if len(part) >= 3 and part.isascii():
                        terms.add(part)
        atom_seq = n.get("atom_sequence")
        if isinstance(atom_seq, list):
            for a in atom_seq[:6]:
                if isinstance(a, str) and len(a) >= 2:
                    terms.add(a.lower())
    return terms


def _route_case(
    gr: Any,
    *,
    text: str,
    node_map: dict[str, dict[str, Any]],
    adj: dict[str, list[dict[str, Any]]],
    seed_topk: int = 8,
    max_hops: int = 2,
    max_edges: int = 80,
) -> dict[str, Any]:
    kws = gr._keywords(text)
    seeds = gr._seed_nodes(list(node_map.values()), kws, topk=seed_topk)
    seed_ids = [n["node_id"] for n in seeds if n.get("node_id")]
    expanded, traversed = gr._multi_hop_expand(
        seed_ids=seed_ids,
        adj=adj,
        max_hops=max_hops,
        max_edges=max_edges,
    )
    selected = [node_map[nid] for nid in sorted(expanded) if nid in node_map]
    return {
        "seed_keywords": kws[:12],
        "seed_node_count": len(seed_ids),
        "expanded_node_count": len(expanded),
        "traversed_edge_count": len(traversed),
        "anchor_terms": sorted(_anchor_terms_from_nodes(selected)),
    }


def _build_graph_must_keep(case_routes: list[dict[str, Any]]) -> set[str]:
    union: set[str] = set()
    for row in case_routes:
        for t in row.get("anchor_terms") or []:
            if len(t) >= 3:
                union.add(t)
    extra = sorted(union)[:MAX_GRAPH_TERMS]
    return BASE_MUST_KEEP | set(extra)


def _base_eval_kwargs() -> dict[str, Any]:
    baseline = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    return {
        "source_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "mode": "experimental",
        "strategy": str(selected.get("strategy", "A")),
        "intensity": str(selected.get("intensity", "extreme")),
        "jaccard_drop_threshold_pp": threshold_pp,
        "baseline_avg_jaccard": baseline_j,
        "general_max_saving_rate": float(selected.get("general_max_saving_rate", 0.35)),
        "sensitive_max_saving_rate": float(selected.get("sensitive_max_saving_rate", 0.3)),
        "hangul_max_saving_rate": float(selected.get("hangul_max_saving_rate", 0.6)),
        "use_domain_router": True,
        "include_gematria_metadata": True,
        "include_gematria_4d_bridge": True,
        "include_cee_core": True,
        "use_master_codebook_lexicon_v1": True,
        "domain_relaxed_max_saving_overrides": {"ssot": 0.45},
        "domain_relaxed_max_saving_case_allowlist": TOP5,
    }


def _metrics(report: dict[str, Any]) -> dict[str, Any]:
    cm = report.get("compression_metrics") or {}
    qg = report.get("quality_gate") or {}
    saving = float(cm.get("global_token_saving_rate", 0.0))
    jaccard = float(cm.get("avg_reconstruction_fidelity_jaccard", 0.0))
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": jaccard,
        "min_reconstruction_fidelity_jaccard": float(
            cm.get("min_reconstruction_fidelity_jaccard", 0.0)
        ),
        "sensitive_integrity_ok": bool(qg.get("sensitive_integrity_ok")),
        "ultra_saving_policy_ok": bool(qg.get("ultra_saving_policy_ok")),
        "apply_gematria_4d_bridge_policy": bool(
            (report.get("run_config") or {}).get("apply_gematria_4d_bridge_policy")
        ),
    }


def _eval_combo(
    src: dict[str, Any],
    combo_id: str,
    must_keep: set[str],
    *,
    bridge: bool,
    allowlist: frozenset[str] | None = None,
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    report = evaluate_report(
        src,
        must_keep=must_keep,
        apply_gematria_4d_bridge_policy=bridge,
        bridge_policy_domain_allowlist=allowlist,
        **kw,
    )
    mk_sample = sorted(must_keep)[:20]
    return {
        "combo_id": combo_id,
        "must_keep_count": len(must_keep),
        "must_keep_sample": mk_sample,
        "metrics": _metrics(report),
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

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    case_routes: list[dict[str, Any]] = []
    for case in src.get("compression_cases") or []:
        cid = str(case.get("id", ""))
        raw = str(case.get("raw_text", ""))
        route = _route_case(gr, text=raw, node_map=node_map, adj=adj)
        route["case_id"] = cid
        case_routes.append(route)

    graph_mk = _build_graph_must_keep(case_routes)
    cases_with_hits = sum(1 for r in case_routes if r.get("expanded_node_count", 0) > 0)

    combos = [
        _eval_combo(src, "economy_baseline", BASE_MUST_KEEP, bridge=False),
        _eval_combo(src, "graphrag_must_keep", graph_mk, bridge=False),
        _eval_combo(
            src,
            "graphrag_selective_ssot",
            graph_mk,
            bridge=True,
            allowlist=frozenset({"ssot"}),
        ),
        _eval_combo(src, "graphrag_bridge_full", graph_mk, bridge=True),
    ]

    baseline_m = combos[0]["metrics"]
    graph_m = combos[1]["metrics"]
    deltas = {
        k: round(graph_m[k] - baseline_m[k], 6)
        if isinstance(baseline_m[k], (int, float))
        else None
        for k in ("global_token_saving_rate", "avg_reconstruction_fidelity_jaccard")
    }

    doc = {
        "schema": "comp_graphrag_philosophy_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "b_track_research_only",
        "data_fabric_module_registry": "docs/final/artifacts/data_fabric_module_registry_v1_latest.json",
        "graphrag_ssot": "CONSTITUTION §31.2a · global_atom_network_*_latest.jsonl",
        "worldview_ssot": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
        "active_report_untouched": True,
        "gate_status": status,
        "graph_routing": {
            "cases_total": len(case_routes),
            "cases_with_graph_expansion": cases_with_hits,
            "graph_must_keep_union_size": len(graph_mk),
            "graph_terms_added_beyond_base": len(graph_mk - BASE_MUST_KEEP),
        },
        "case_routes_sample": case_routes[:5],
        "combos": combos,
        "deltas_graphrag_vs_baseline": deltas,
        "interpretation": {
            "is_graphrag_complete": False,
            "note": (
                "Atom-network GraphRAG pilot only — not full 31k verse GraphRAG product. "
                "Anchors inject must_keep inductive bias; Track A unchanged unless human gate."
            ),
            "pareto": (
                "If graphrag_must_keep does not beat economy on both saving and jaccard, "
                "GraphRAG stays R&D channel (M1–M9 fabric) separate from MS 47.5% headline."
            ),
        },
        "compare_prior_combo_sweep": "reports/constitution/btrack_pilot/comp_combo_optimal_sweep_v1.json",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "graph_terms_added": len(graph_mk - BASE_MUST_KEEP),
                "deltas": deltas,
                "combos": {c["combo_id"]: c["metrics"] for c in combos},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
