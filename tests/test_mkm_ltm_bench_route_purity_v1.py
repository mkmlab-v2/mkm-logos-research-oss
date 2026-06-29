"""Tests for LTM bench 2/3 + inject contract ([HYPO] / B-track)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ltm_route_accuracy_v1 import (  # noqa: E402
    blind_top1_concept,
    build_graph_only_cases,
    evaluate_case,
    load_corpus,
)
from mkm_ltm_lane_purity_lib_v1 import (  # noqa: E402
    lane_purity_violations,
    load_inject_contract,
)
from mkm_long_term_memory_graph_lib_v1 import load_graph  # noqa: E402

GRAPH_PATH = ROOT / "storage" / "meta" / "mkm_long_term_memory_graph_v1.json"
CORPUS_PATH = ROOT / "docs" / "final" / "artifacts" / "mkm_ltm_route_accuracy_corpus_v1.json"
CONTRACT_PATH = ROOT / "docs" / "final" / "artifacts" / "mkm_ltm_inject_contract_v1.json"


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_route_accuracy_corpus_schema_and_cases() -> None:
    cases = load_corpus(CORPUS_PATH)
    assert len(cases) >= 24
    for case in cases:
        assert case.get("query")
        assert case.get("expect_top1_any")


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_route_accuracy_evaluate_case_hit() -> None:
    graph = load_graph(GRAPH_PATH)
    cases = load_corpus(CORPUS_PATH)
    taeyang = next(c for c in cases if c["id"] == "taeyang_containment")
    result = evaluate_case(graph, taeyang)
    assert result["graph_top1"] == "sasang_taeyang_containment"
    assert result["graph_top1_hit"] is True
    assert result["resolved_lane"] == "oracle"


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_blind_top1_returns_concept() -> None:
    graph = load_graph(GRAPH_PATH)
    top1 = blind_top1_concept(graph, "fact lock CONSTITUTION path")
    assert top1 in {"fact_lock_implementation", "verify_p0_constitution_paths"}


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_graph_only_hit_adversarial_cases() -> None:
    graph = load_graph(GRAPH_PATH)
    cases = load_corpus(CORPUS_PATH)
    meta = next(c for c in cases if c["id"] == "twelve_ai_meta_routing")
    result = evaluate_case(graph, meta)
    assert result["graph_top1"] == "twelve_ai_routing_contract"
    assert result["graph_top1_hit"] is True
    assert result["graph_only_hit"] is True
    assert result["blind_top1_hit"] is False


def test_inject_contract_schema() -> None:
    contract = load_inject_contract(CONTRACT_PATH)
    assert contract["schema"] == "mkm_ltm_inject_contract_v1"
    assert contract["lane_ops_pack"]["max_nodes_per_lane"] == 4
    assert contract["ltm_routing"]["max_ltm_concepts"] == 5


def test_lane_purity_ms_forbidden() -> None:
    flags = lane_purity_violations("ms", "track a 47.5% jaccard headline")
    assert any("47.5%" in f for f in flags)


def test_lane_purity_oracle_forbidden() -> None:
    flags = lane_purity_violations("oracle", "MULTILENS_ULTRA active report")
    assert any("MULTILENS_ULTRA" in f for f in flags)


def test_lane_purity_clean_ms() -> None:
    flags = lane_purity_violations("ms", "FAIL-COMP-004 HOLD submission")
    assert flags == []


@pytest.mark.skipif(
    not (ROOT / "storage" / "meta" / "mkm_ops_memory_index_v1.json").is_file(),
    reason="ops index not built",
)
def test_check_lane_purity_script_exit_zero() -> None:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_mkm_ltm_lane_purity_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_sasang_gematria_sidecar_routing_hit() -> None:
    graph = load_graph(GRAPH_PATH)
    cases = load_corpus(CORPUS_PATH)
    sidecar = next(c for c in cases if c["id"] == "sasang_gematria_sidecar_routing")
    result = evaluate_case(graph, sidecar)
    assert result["graph_top1"] == "sasang_routing_sidecar_gematria_path"
    assert result["graph_top1_hit"] is True
    assert result["resolved_lane"] == "oracle"


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_route_accuracy_bench_script_exit_zero() -> None:
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "bench_mkm_ltm_route_accuracy_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out_path = ROOT / "reports" / "mkm_ltm_route_accuracy_bench_v1_latest.json"
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    agg = doc["aggregate"]
    assert agg["graph_top1_hit_rate"] >= 0.75
    assert agg["delta_graph_minus_blind"] > 0
    assert agg["graph_only_hit_count"] >= 1
    graph_only = doc["graph_only_cases"]
    assert len(graph_only) == agg["graph_only_hit_count"]
    for case in graph_only:
        assert case["id"]
        assert case["query"]
        assert case["blind_top1"]
        assert case["graph_top1"]
        assert case["cause"]


@pytest.mark.skipif(not GRAPH_PATH.is_file(), reason="graph not built")
def test_build_graph_only_cases_shape() -> None:
    graph = load_graph(GRAPH_PATH)
    cases = load_corpus(CORPUS_PATH)
    results = [evaluate_case(graph, case) for case in cases]
    graph_only = build_graph_only_cases(results, graph)
    assert len(graph_only) >= 1
    meta = next(c for c in graph_only if c["id"] == "twelve_ai_meta_routing")
    assert meta["graph_top1"] == "twelve_ai_routing_contract"
    assert meta["blind_top1"] == "ltm_graph_self_meta"
