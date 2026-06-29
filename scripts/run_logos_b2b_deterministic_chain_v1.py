#!/usr/bin/env python3
"""B2B 3-stage deterministic chain — Alpha/Beta rules + dialectical resolution [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_b2b_deterministic_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _node_by_type(nodes: list[dict[str, Any]], ntype: str) -> dict[str, Any] | None:
    for n in nodes:
        if n.get("type") == ntype:
            return n
    return None


def _stage2_alpha_beta(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes") or []
    rels = graph.get("relationships") or []
    ant = _node_by_type(nodes, "Antecedent")
    inter = _node_by_type(nodes, "Intermediary")
    cons = _node_by_type(nodes, "Consequent")
    constr = _node_by_type(nodes, "Constraints")

    violations: list[dict[str, Any]] = []
    rel_types = {(r["source"], r["target"]): r.get("relation_type") for r in rels}

    if ant and constr and inter and cons:
        obstructs = rel_types.get((constr["id"], inter["id"])) == "obstructs"
        triggers = rel_types.get((ant["id"], inter["id"])) == "triggers"
        to_outcome = rel_types.get((inter["id"], cons["id"])) in ("dependency_path", "causes", "triggers")
        bypass_nodes = [n for n in nodes if n.get("type") not in ("Antecedent", "Constraints", "Consequent")]
        has_bypass = len(bypass_nodes) > 1

        if obstructs and triggers and not has_bypass:
            violations.append(
                {
                    "rule": "Alpha",
                    "path": [ant["id"], inter["id"], cons["id"]],
                    "issue": "constraint_obstructs_without_documented_bypass",
                }
            )
        if triggers and to_outcome and not any(r.get("relation_type") == "co_occurrence" for r in rels):
            violations.append(
                {
                    "rule": "Beta",
                    "path": [ant["id"], inter["id"], cons["id"]],
                    "issue": "co_occurrence_control_absent_for_shared_intermediary",
                    "severity": "warning",
                }
            )

    return {
        "violations": violations,
        "violation_count": len(violations),
        "alpha_triggered": any(v["rule"] == "Alpha" for v in violations),
        "beta_triggered": any(v["rule"] == "Beta" for v in violations),
        "coherence_ok": len([v for v in violations if v.get("severity") != "warning"]) == 0,
    }


def _stage3_resolution(stage2: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    adjustments: list[dict[str, Any]] = []
    hitl_points: list[str] = []
    for v in stage2.get("violations") or []:
        if v["rule"] == "Alpha":
            adjustments.append(
                {
                    "target_violation": v,
                    "adjustment_node": {
                        "id": "ADJ_BYPASS",
                        "type": "Intermediary",
                        "description": "Documented_bypass_evidence_path",
                    },
                    "proposed_edges": [
                        {"source": v["path"][0], "target": "ADJ_BYPASS", "relation_type": "triggers"},
                        {"source": "ADJ_BYPASS", "target": v["path"][2], "relation_type": "dependency_path"},
                    ],
                }
            )
            hitl_points.append("verify_bypass_evidence_before_external_send")
        elif v["rule"] == "Beta":
            adjustments.append(
                {
                    "target_violation": v,
                    "adjustment_node": {
                        "id": "ADJ_COOC",
                        "type": "Intermediary",
                        "description": "Co_occurrence_synchronization_gate",
                    },
                    "proposed_edges": [
                        {"source": v["path"][1], "target": "ADJ_COOC", "relation_type": "co_occurrence"},
                    ],
                }
            )
            hitl_points.append("human_review_shared_intermediary_timing")

    if not hitl_points:
        hitl_points.append("standard_send_gate_human_signoff")

    return {
        "adjustments": adjustments,
        "hitl_checkpoints": hitl_points,
        "recovery_topology_ready": len(adjustments) > 0 or stage2.get("coherence_ok"),
    }


def _apply_adjustments(graph: dict[str, Any], stage3: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes") or [])
    rels = list(graph.get("relationships") or [])
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    rel_keys = {(r.get("source"), r.get("target"), r.get("relation_type")) for r in rels}
    for adj in stage3.get("adjustments") or []:
        an = adj.get("adjustment_node") or {}
        if an.get("id") and an["id"] not in node_ids:
            nodes.append(an)
            node_ids.add(an["id"])
        for e in adj.get("proposed_edges") or []:
            key = (e.get("source"), e.get("target"), e.get("relation_type"))
            if key not in rel_keys:
                rels.append(e)
                rel_keys.add(key)
    out = dict(graph)
    out["nodes"] = nodes
    out["relationships"] = rels
    return out


def build(*, psi_doc: dict[str, Any] | None, hot_reload: bool = True) -> dict[str, Any]:
    graph = (psi_doc or {}).get("logic_graph") or {"nodes": [], "relationships": []}
    stage1 = {"logic_graph": graph, "stage": "logic_extraction_gate"}
    stage2_report = _stage2_alpha_beta(graph)
    stage3 = _stage3_resolution(stage2_report, graph)
    converged_graph = graph
    reload_iters = 0
    while hot_reload and reload_iters < 3 and (stage2_report.get("violations") or []):
        converged_graph = _apply_adjustments(converged_graph, stage3)
        stage2_report = _stage2_alpha_beta(converged_graph)
        stage3 = _stage3_resolution(stage2_report, converged_graph)
        reload_iters += 1

    return {
        "schema": "logos_b2b_deterministic_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "structure_transplant_only": True,
        "theology_to_sales_forbidden": True,
        "stages": {
            "stage1_logic_extraction": stage1,
            "stage2_intertextual_conflict": stage2_report,
            "stage3_dialectical_resolution": stage3,
            "stage4_hot_reload_converged": {
                "logic_graph": converged_graph,
                "reload_iterations": reload_iters,
                "violations_remaining": stage2_report.get("violation_count"),
            },
        },
        "summary": {
            "chain_complete": True,
            "coherence_ok": stage2_report.get("coherence_ok"),
            "beta_resolved": not stage2_report.get("beta_triggered"),
            "alpha_resolved": not stage2_report.get("alpha_triggered"),
            "hot_reload_iterations": reload_iters,
            "hitl_required": True,
            "hitl_checkpoint_count": len(stage3.get("hitl_checkpoints") or []),
        },
        "reproduce": "py scripts/run_logos_b2b_deterministic_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--psi", type=Path, default=ROOT / "reports/logos_psi_logic_extraction_v1_latest.json")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    psi_doc = _load(args.psi)
    if not psi_doc:
        import subprocess
        import sys

        subprocess.run([sys.executable, "scripts/build_logos_psi_logic_extraction_v1.py"], cwd=ROOT, check=True)
        psi_doc = _load(args.psi)

    doc = build(psi_doc=psi_doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc["summary"]["chain_complete"] is True
    print(
        json.dumps(
            {
                "ok": ok,
                "coherence_ok": doc["summary"]["coherence_ok"],
                "hitl_checkpoints": doc["summary"]["hitl_checkpoint_count"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
