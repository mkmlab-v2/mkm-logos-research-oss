#!/usr/bin/env python3
"""[HYPO] Logos OL GraphRAG bridge — FACT alignment rollup vs bridge doc v1."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DOC = ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md"
OUT = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"

PHASE0_ARTIFACTS = {
    "concept_bridge": "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json",
    "seed_chain": "docs/final/artifacts/logos_graph_seed_chain_v1_latest.json",
    "corpus_bundle": "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
    "wire_poc": "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json",
    "wire_profile": "docs/final/artifacts/logos_graph_wire_profile_v1_latest.json",
    "atoms_summary": "reports/constitution/btrack_pilot/original_language_master_atoms_summary_latest.json",
}
PHASE1_ARTIFACTS = {
    "lemma_edges_manifest": "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json",
    "lemma_edges_jsonl": "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl",
    "corpus_split": "reports/logos_lemma_verse_edges_corpus_split_v1_latest.json",
    "subgraph_router": "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json",
}
PHASE2_ARTIFACTS = {
    "concept_bridge_registry": "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
    "llm_plan": "docs/final/artifacts/logos_concept_bridge_llm_plan_v1_latest.json",
    "governance_gate": "reports/logos_concept_bridge_governance_v1_latest.json",
    "human_gate_queue": "docs/final/artifacts/logos_concept_bridge_human_gate_queue_v1_latest.json",
}
PHASE3_ARTIFACTS = {
    "subgraph_replay": "reports/subgraph_router_replay_summary_latest.json",
    "showroom_audit_slice": (
        "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
        "showroom_logos_subgraph_audit_slice_v1.json"
    ),
    "showroom_audit_gate": "reports/showroom_logos_subgraph_audit_slice_gate_v1_latest.json",
    "showroom_wire_poc": (
        "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
        "showroom_logos_graph_wire_rag_poc_v1.json"
    ),
    "oracle_v6_html": (
        "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/"
        "public_showroom_logos_oracle_v6.html"
    ),
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    present: dict[str, bool] = {}
    pointers: dict[str, str] = {}
    for key, rel in PHASE0_ARTIFACTS.items():
        p = ROOT / rel.replace("/", "\\")
        present[key] = p.is_file()
        if present[key]:
            pointers[key] = rel

    bundle = _read(PHASE0_ARTIFACTS["corpus_bundle"]) or {}
    bridge = _read(PHASE0_ARTIFACTS["concept_bridge"]) or {}
    wire = _read(PHASE0_ARTIFACTS["wire_poc"]) or {}

    phase1_present: dict[str, bool] = {}
    phase1_pointers: dict[str, str] = {}
    for key, rel in PHASE1_ARTIFACTS.items():
        p = ROOT / rel.replace("/", "\\")
        phase1_present[key] = p.is_file()
        if phase1_present[key]:
            phase1_pointers[key] = rel

    lemma_manifest = _read(PHASE1_ARTIFACTS["lemma_edges_manifest"]) or {}
    split_doc = _read(PHASE1_ARTIFACTS["corpus_split"]) or {}
    phase1_complete = (
        all(phase1_present.values())
        and int(lemma_manifest.get("edge_count") or 0) >= 10
        and split_doc.get("gate_pass") is True
    )

    phase2_present: dict[str, bool] = {}
    phase2_pointers: dict[str, str] = {}
    for key, rel in PHASE2_ARTIFACTS.items():
        p = ROOT / rel.replace("/", "\\")
        phase2_present[key] = p.is_file()
        if phase2_present[key]:
            phase2_pointers[key] = rel

    registry_doc = _read(PHASE2_ARTIFACTS["concept_bridge_registry"]) or {}
    governance_doc = _read(PHASE2_ARTIFACTS["governance_gate"]) or {}
    queue_doc = _read(PHASE2_ARTIFACTS["human_gate_queue"]) or {}
    phase2_complete = (
        all(phase2_present.values())
        and int(registry_doc.get("human_reviewed_count") or 0) >= 1
        and registry_doc.get("governance_warning_zero_human") is False
        and float(registry_doc.get("human_reviewed_ratio") or 0) >= 0.5
        and governance_doc.get("gate_pass") is True
        and int(governance_doc.get("llm_bridge_count") or 0) >= 1
    )

    phase3_present: dict[str, bool] = {}
    phase3_pointers: dict[str, str] = {}
    for key, rel in PHASE3_ARTIFACTS.items():
        p = ROOT / rel.replace("/", "\\")
        phase3_present[key] = p.is_file()
        if phase3_present[key]:
            phase3_pointers[key] = rel

    slice_gate_doc = _read(PHASE3_ARTIFACTS["showroom_audit_gate"]) or {}
    replay_doc = _read(PHASE3_ARTIFACTS["subgraph_replay"]) or {}
    slice_doc = _read(PHASE3_ARTIFACTS["showroom_audit_slice"]) or {}
    v6_html_path = ROOT / PHASE3_ARTIFACTS["oracle_v6_html"].replace("/", "\\")
    subgraph_audit_ui_ok = False
    if v6_html_path.is_file():
        html = v6_html_path.read_text(encoding="utf-8")
        subgraph_audit_ui_ok = (
            "renderSubgraphAuditPanel" in html
            and "showroom_logos_subgraph_audit_slice_v1.json" in html
        )
    phase3_complete = (
        all(phase3_present.values())
        and replay_doc.get("pass") is True
        and int(replay_doc.get("pass_count") or 0) >= 12
        and slice_gate_doc.get("gate_pass") is True
        and slice_doc.get("schema_version") == "showroom_logos_subgraph_audit_slice_v1"
        and subgraph_audit_ui_ok is True
    )

    gaps: list[str] = []
    if not phase1_complete:
        gaps.append("logos_lemma_verse_edges_v1 builder + corpus split gate (Phase 1)")
    if not phase2_complete:
        gaps.append("concept_bridge LLM layer + human_reviewed ratio (Phase 2)")
    if not phase3_complete:
        gaps.append("subgraph router showroom audit panel (Phase 3)")
    if bundle.get("alignment", {}).get("graph_refs_not_in_corpus_sample"):
        gaps.append(
            "corpus ref drift: "
            + ",".join(bundle["alignment"]["graph_refs_not_in_corpus_sample"])
        )

    return {
        "schema": "logos_ol_graph_bridge_alignment_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "bridge_doc": str(BRIDGE_DOC.relative_to(ROOT)).replace("\\", "/"),
        "phase0_complete": all(present.values()),
        "phase1_complete": phase1_complete,
        "phase2_complete": phase2_complete,
        "phase3_complete": phase3_complete,
        "artifacts_present": present,
        "artifact_pointers": pointers,
        "phase1_artifacts_present": phase1_present,
        "phase1_artifact_pointers": phase1_pointers,
        "phase2_artifacts_present": phase2_present,
        "phase2_artifact_pointers": phase2_pointers,
        "phase3_artifacts_present": phase3_present,
        "phase3_artifact_pointers": phase3_pointers,
        "lemma_edge_count": lemma_manifest.get("edge_count"),
        "corpus_split_gate_pass": split_doc.get("gate_pass"),
        "concept_bridge_registry_count": registry_doc.get("bridge_count"),
        "concept_bridge_human_reviewed_ratio": registry_doc.get("human_reviewed_ratio"),
        "concept_bridge_governance_warning_zero_human": registry_doc.get("governance_warning_zero_human"),
        "concept_bridge_llm_bridge_count": governance_doc.get("llm_bridge_count"),
        "concept_bridge_governance_gate_pass": governance_doc.get("gate_pass"),
        "human_gate_queue_count": queue_doc.get("queue_count"),
        "subgraph_replay_pass_count": replay_doc.get("pass_count"),
        "showroom_audit_slice_gate_pass": slice_gate_doc.get("gate_pass"),
        "corpus_bundle_alignment": bundle.get("alignment"),
        "concept_bridge_path_count": len(bridge.get("paths") or []),
        "wire_honest_metrics": wire.get("honest_metrics"),
        "phase_gaps": gaps,
        "reproduce_phase0": "powershell -File scripts/Run-LogosOlGraphBridgeParallel_v1.ps1",
        "reproduce_phase1": "py scripts/run_logos_ol_graph_bridge_phase1_chain_v1.py",
        "reproduce_phase2": "py scripts/run_logos_ol_graph_bridge_phase2_chain_v1.py",
        "reproduce_phase3": "py scripts/run_logos_ol_graph_bridge_phase3_chain_v1.py",
        "pytest": "py -m pytest tests/test_build_showroom_logos_subgraph_audit_slice_v1.py -q -k test_build",
    }


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc.get("phase0_complete") is True
    if ok:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_build_showroom_logos_subgraph_audit_slice_v1.py",
                "-q",
                "-k",
                "test_build",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        ok = r.returncode == 0
        doc["pytest_exit_code"] = r.returncode
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(OUT),
                "phase0_complete": doc["phase0_complete"],
                "phase1_complete": doc.get("phase1_complete"),
                "phase2_complete": doc.get("phase2_complete"),
                "phase3_complete": doc.get("phase3_complete"),
            }
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
