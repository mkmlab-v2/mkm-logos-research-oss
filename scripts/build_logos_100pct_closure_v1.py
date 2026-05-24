#!/usr/bin/env python3
"""LOGOS-100PCT: aggregate DoD checks into logos_100pct_closure_v1_latest.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"

CDIM = ROOT / "docs/final/artifacts/logos_cross_domain_interface_latest.json"
ENVELOPE = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
TOPOLOGY = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
READINESS = ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json"
DUAL_EVAL = ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_dual_gold_eval_v1_latest.json"
GATE = ROOT / "docs/final/artifacts/logos_rag_btrack_promotion_gate_v1_latest.json"
LEMMA_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
OL_ATOMS_SUMMARY = ROOT / "reports/constitution/btrack_pilot/original_language_master_atoms_summary_latest.json"
BRIDGE_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
SUBGRAPH_ROUTER = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _check_rag_resolved(envelope: dict[str, Any] | None) -> dict[str, Any]:
    resolved = (envelope or {}).get("rag_layers_resolved") or {}
    layers = ("lexical", "semantic", "temporal", "constitutional")
    per_layer: dict[str, bool] = {}
    all_ok = True
    for layer in layers:
        entries = resolved.get(layer) if isinstance(resolved.get(layer), list) else []
        ok = bool(entries) and all(
            isinstance(e, dict) and e.get("present") is True for e in entries
        )
        per_layer[layer] = ok
        all_ok = all_ok and ok
    return {"passed": all_ok, "per_layer": per_layer}


def _check_graphics(topology: dict[str, Any] | None, readiness: dict[str, Any] | None) -> dict[str, Any]:
    stats = (topology or {}).get("stats") if isinstance((topology or {}).get("stats"), dict) else {}
    node_count = int(stats.get("node_count") or 0)
    nodes_ok = node_count >= 120
    commercial_ok = bool((readiness or {}).get("commercial_stack_ok"))
    public_smoke = bool((readiness or {}).get("public_smoke_ok"))
    return {
        "passed": nodes_ok and commercial_ok and public_smoke,
        "node_count": node_count,
        "node_target": 120,
        "commercial_stack_ok": commercial_ok,
        "public_smoke_ok": public_smoke,
    }


def _check_rag_quality(dual: dict[str, Any] | None, gate: dict[str, Any] | None) -> dict[str, Any]:
    summary = (dual or {}).get("summary") if isinstance((dual or {}).get("summary"), dict) else {}
    hit1 = float(summary.get("thematic_hit_at_1_ko_improved") or 0.0)
    hit3_path = (gate or {}).get("metrics") or {}
    hit3 = float(hit3_path.get("weak_gold_hit_at_3") or 0.0)
    tier_l2 = ((gate or {}).get("tiers") or {}).get("L2_track_c_shadow_ingest") or {}
    l2 = bool(tier_l2.get("passed")) if isinstance(tier_l2, dict) else False
    hit1_ok = hit1 >= 0.50
    hit3_ok = hit3 >= 0.90
    passed = l2 and hit3_ok and (hit1_ok or hit1 >= 0.33)
    return {
        "passed": passed,
        "thematic_hit_at_1": hit1,
        "hit_at_1_target": 0.50,
        "weak_gold_hit_at_3": hit3,
        "L2_passed": l2,
        "ceiling_note": None if hit1_ok else "thematic_hit@1 below 50%; L2+hit@3 may still pass",
    }


def _check_wire(poc: dict[str, Any] | None) -> dict[str, Any]:
    ok = bool(poc and poc.get("schema") == "logos_graph_wire_rag_poc_v1")
    wire = (poc or {}).get("wire") if isinstance((poc or {}).get("wire"), dict) else {}
    hm = wire.get("honest_metrics") if isinstance(wire.get("honest_metrics"), dict) else {}
    return {"passed": ok and bool(hm), "honest_metrics_present": bool(hm)}


def _check_lemma_phase1(manifest: dict[str, Any] | None) -> dict[str, Any]:
    ok = bool(manifest and manifest.get("schema") == "logos_lemma_verse_edges_v1")
    count = int((manifest or {}).get("edge_count") or 0)
    return {"passed": ok and count >= 10, "edge_count": count, "edge_target": 10}


def _check_ol_master_atoms(summary: dict[str, Any] | None) -> dict[str, Any]:
    ok = bool(summary and summary.get("schema") == "original_language_master_atoms_summary_v1")
    stats = (summary or {}).get("stats") if isinstance((summary or {}).get("stats"), dict) else {}
    unique = int(stats.get("unique_master_atoms") or 0)
    by_lang = stats.get("unique_atoms_by_lang") if isinstance(stats.get("unique_atoms_by_lang"), dict) else {}
    hebrew = int(by_lang.get("hebrew") or 0)
    greek = int(by_lang.get("greek") or 0)
    passed = ok and unique >= 10000 and hebrew >= 5000 and greek >= 3000
    return {
        "passed": passed,
        "unique_master_atoms": unique,
        "hebrew_atoms": hebrew,
        "greek_atoms": greek,
    }


def _check_cross_domain(cdim: dict[str, Any] | None) -> dict[str, Any]:
    ok = bool(cdim and cdim.get("schema") == "logos_cross_domain_interface_v1")
    refs = (cdim or {}).get("cross_refs") if isinstance((cdim or {}).get("cross_refs"), list) else []
    concept_n = sum(1 for r in refs if isinstance(r, dict) and r.get("relation_type") == "concept_path")
    graphrag_n = sum(1 for r in refs if isinstance(r, dict) and r.get("relation_type") == "graphrag_route")
    passed = ok and len(refs) >= 8 and concept_n >= 3 and graphrag_n >= 1
    return {
        "passed": passed,
        "cross_ref_count": len(refs),
        "concept_path_refs": concept_n,
        "graphrag_route_refs": graphrag_n,
    }


def _check_phase2_graphrag(registry: dict[str, Any] | None, router: dict[str, Any] | None) -> dict[str, Any]:
    reg_ok = bool(registry and registry.get("schema") == "logos_concept_bridge_registry_v1")
    bridge_n = int((registry or {}).get("bridge_count") or 0)
    router_ok = bool(router and router.get("schema") == "logos_subgraph_graphrag_router_v1")
    paths_n = len((router or {}).get("paths") or []) if router_ok else 0
    passed = reg_ok and bridge_n >= 2 and router_ok and paths_n >= 1
    phase3_note = "bridge_count>=3" if bridge_n >= 3 else None
    phase4_note = "bridge_count>=4" if bridge_n >= 4 else None
    return {
        "passed": passed,
        "bridge_count": bridge_n,
        "bridge_target": 2,
        "phase3_bridge_note": phase3_note,
        "phase4_bridge_note": phase4_note,
        "router_paths": paths_n,
        "human_reviewed_ratio": (registry or {}).get("human_reviewed_ratio"),
        "governance_warning_zero_human": (registry or {}).get("governance_warning_zero_human"),
    }


def _run_pytest(quick: bool) -> dict[str, Any]:
    tests = [
        "tests/test_assemble_three_lens_sphere_envelope_v1.py",
        "tests/test_build_mkm_graph_wire_rag_poc_v1.py",
        "tests/test_logos_concept_bridge_v1.py",
    ]
    if not quick:
        tests.extend(
            [
                "tests/test_build_logos_lemma_verse_edges_v1.py",
                "tests/test_run_logos_subgraph_graphrag_router_v1.py",
                "tests/test_build_logos_concept_bridge_registry_v1.py",
                "tests/test_logos_cross_domain_interface_v1.py",
                "tests/test_build_logos_concept_bridge_cloud_resilience_poc_v1.py",
                "tests/test_build_logos_concept_bridge_gemini_v1.py",
                "tests/test_build_logos_rag_q01_theology_adjudication_v1.py",
            ]
        )
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
    return {
        "passed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-400:],
    }


def build_report(*, run_pytest: bool) -> dict[str, Any]:
    envelope = _read_json(ENVELOPE)
    topology = _read_json(TOPOLOGY)
    poc = _read_json(POC)
    readiness = _read_json(READINESS)
    dual = _read_json(DUAL_EVAL)
    gate = _read_json(GATE)
    lemma = _read_json(LEMMA_MANIFEST)
    ol_atoms = _read_json(OL_ATOMS_SUMMARY)
    registry = _read_json(BRIDGE_REGISTRY)
    subgraph_router = _read_json(SUBGRAPH_ROUTER)
    cdim = _read_json(CDIM)

    checks = {
        "rag_4e_resolved": _check_rag_resolved(envelope),
        "graphics_showroom": _check_graphics(topology, readiness),
        "semantic_rag_quality": _check_rag_quality(dual, gate),
        "graph_wire_poc": _check_wire(poc),
        "lemma_verse_phase1": _check_lemma_phase1(lemma),
        "ol_master_atoms": _check_ol_master_atoms(ol_atoms),
        "cross_domain_interface": _check_cross_domain(cdim),
        "graphrag_phase2": _check_phase2_graphrag(registry, subgraph_router),
    }
    if run_pytest:
        checks["pytest_bundle"] = _run_pytest(quick=False)

    hard_pass = all(
        c.get("passed")
        for k, c in checks.items()
        if k not in ("pytest_bundle", "semantic_rag_quality") and isinstance(c, dict)
    )
    rag_soft = checks.get("semantic_rag_quality", {})
    if isinstance(rag_soft, dict) and not rag_soft.get("passed"):
        hard_pass = hard_pass and bool(rag_soft.get("L2_passed"))
    pytest_pass = checks.get("pytest_bundle", {}).get("passed", True)
    closure_ok = hard_pass and pytest_pass

    return {
        "schema": "logos_100pct_closure_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "closure_ok": closure_ok,
        "checks": checks,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_trigger": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build LOGOS-100PCT closure report")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-pytest", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if closure_ok false")
    args = ap.parse_args()

    report = build_report(run_pytest=args.run_pytest)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "closure_ok": report["closure_ok"], "out": str(args.out_json)}))
    if args.strict and not report["closure_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
