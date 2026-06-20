from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_registry_gate_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_mkm_reference_pointer_registry_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "OK" in proc.stdout


def test_registry_has_six_pointers_including_merged() -> None:
    reg = json.loads((ROOT / "storage/meta/mkm_reference_pointer_registry_v1.json").read_text(encoding="utf-8"))
    ids = {p["id"] for p in reg["pointers"]}
    assert len(ids) == 6
    assert "ref:research:nextgen_hybrid_merged" in ids
    assert "ref:python:asyncio:TaskGroup" in ids
    for ptr in reg["pointers"]:
        assert ptr["inject_policy"] == "on_demand_only"
        assert "ops_memory_index" in ptr["forbidden_merge_into"]


def test_build_knowledge_catalog() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_knowledge_catalog_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "docs/final/artifacts/mkm_knowledge_catalog_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_knowledge_catalog_v1"
    assert doc["registry_gate_ok"] is True
    assert doc["vaults"]["reference_cold"]["pointer_count"] == 6
    assert doc["vaults"]["governance_ltm"]["ops_node_count"] >= 1
    assert doc["research_ssot"]["merged_lit_review_present"] is True
    assert doc["research_ssot"]["registry_pointer_id"] == "ref:research:nextgen_hybrid_merged"
    assert doc["vaults"]["governance_ltm"]["ltm_graph_node_count"] >= 1
