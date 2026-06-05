"""Logos subgraph GraphRAG router v1 smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"
REGISTRY_BUILDER = ROOT / "scripts/build_logos_concept_bridge_registry_v1.py"
COVENANT_BUILDER = ROOT / "scripts/build_logos_concept_bridge_covenant_crisis_poc_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_subgraph_graphrag_router_v1.schema.json"


def test_logos_subgraph_router_covenant_query(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query-id",
            "q01",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["bridges_matched"] >= 1
    assert len(doc["paths"]) >= 1
    assert any("Ps.89" in v or "Jer.31" in v or "Job.24" in v for v in doc["verse_ids"])


def test_logos_subgraph_router_explicit_query_overrides_gold_id(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router_override.json"
    explicit = "언약이 흔들릴 때 심판의 경고와 회복"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query-id",
            "q03",
            "--query",
            explicit,
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["query"] == explicit


def test_logos_subgraph_router_composite_q03_multi_bridge(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router_q03.json"
    composite = (
        "언약이 흔들릴 때 심판의 경고와 회복의 약속이 동시에 엮이는 성경 경로는 어디인가?"
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            composite,
            "--top-bridges",
            "6",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("policy", {}).get("bridge_selection") == "multi_coverage_v1"
    assert doc["bridges_matched"] >= 3
    bridge_artifacts = {p.get("bridge_artifact") for p in doc["paths"]}
    assert len(bridge_artifacts) >= 3
    assert len(doc["paths"]) >= 3
    lanes = doc.get("theme_lanes_active") or []
    assert "covenant" in lanes
    assert "judgment" in lanes
    assert "restoration" in lanes


def test_logos_subgraph_router_q04_judgment_covenant_chain(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router_q04.json"
    chain_q = (
        "심판의 경고 이후에도 언약의 잔류가 남는다는 성경적 논증은, "
        "어떤 구절·경로(chain)로 연결되는가?"
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            chain_q,
            "--top-bridges",
            "6",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    lanes = doc.get("theme_lanes_active") or []
    assert "covenant" in lanes
    assert "judgment" in lanes
    assert doc["bridges_matched"] >= 2
    assert len(doc["paths"]) >= 2


def test_logos_subgraph_router_q05_hubris_volatility_overlay(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router_q05.json"
    overlay_q = (
        "고문헌의 붕괴·교역(hubris/trade) 서사와 거시 변동성 쇼크 서사 사이에 "
        "구조적으로 대응되는 Logos 경로는 무엇인가?"
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            overlay_q,
            "--top-bridges",
            "6",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    lanes = doc.get("theme_lanes_active") or []
    assert "hubris_trade" in lanes or "judgment" in lanes
    assert "volatility" in lanes
    assert doc["bridges_matched"] >= 3
    assert len(doc["paths"]) >= 9


def test_logos_subgraph_router_canonical_verse_refs_at_source(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    out = tmp_path / "router_canon.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query-id",
            "q02",
            "--gold-json",
            str(ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"),
            "--top-bridges",
            "4",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("policy", {}).get("verse_ref_canonical_at_source") is True
    for vid in doc.get("verse_ids") or []:
        assert not str(vid).startswith("verse_ref:")
        assert not str(vid).startswith("hebrew::")
        assert "." in str(vid)
    for path in doc.get("paths") or []:
        for step in path.get("steps") or []:
            s = str(step)
            if s.startswith(("concept:", "function:", "lemma:", "node:", "mc_", "func_", "lp_")):
                continue
            if s.startswith("verse:"):
                inner = s.split(":", 1)[1]
                assert not inner.startswith("verse_ref:")
                assert "." in inner
                continue
            assert not s.startswith("verse_ref:")
            assert not s.startswith("vr_")


def test_logos_subgraph_router_node_verse_compact_steps(tmp_path: Path) -> None:
    """node_verse_ps23_3 style steps canonicalize at source (P1-1)."""
    risk_off = ROOT / "reports/logos_graphrag_2026_risk_off_latest.json"
    if not risk_off.is_file():
        return
    out = tmp_path / "router_risk_off.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query",
            "야간 risk-off 변동성",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    for path in doc.get("paths") or []:
        for step in path.get("steps") or []:
            s = str(step)
            if s.startswith("node_verse_"):
                pytest.fail(f"uncanon node_verse step remained: {s}")
    # When routing hits stability bridge, compact node steps become canon refs
    graph = json.loads(risk_off.read_text(encoding="utf-8"))
    raw_steps = [
        str(s)
        for p in graph.get("paths") or []
        for s in (p.get("steps") or [])
        if str(s).startswith("node_verse_")
    ]
    if raw_steps:
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_logos_gold_query_eval_report_v1 as ev

        for raw in raw_steps[:3]:
            canon = ev.normalize_verse_ref(raw)
            assert "." in canon and not canon.startswith("node_verse_")


def test_logos_subgraph_router_lemma_contain_boost(tmp_path: Path) -> None:
    lemma_builder = ROOT / "scripts/build_logos_lemma_verse_edges_v1.py"
    registry = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
    subprocess.run([sys.executable, str(COVENANT_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run([sys.executable, str(REGISTRY_BUILDER)], cwd=str(ROOT), check=True)
    subprocess.run(
        [
            sys.executable,
            str(lemma_builder),
            "--registry-json",
            str(registry),
            "--no-graph-heuristic",
        ],
        cwd=str(ROOT),
        check=True,
    )
    out = tmp_path / "router_q01_lemma.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROUTER),
            "--query-id",
            "q01",
            "--gold-json",
            str(ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"),
            "--top-bridges",
            "4",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("policy", {}).get("lemma_contain_boost_v1") is True
    meta = doc.get("lemma_contain_meta") or {}
    assert int(meta.get("edges_considered") or 0) >= 10
    hits = doc.get("lemma_edge_hits") or []
    assert len(hits) >= 1
    assert any(str(h.get("edge_type")) == "CONTAIN" for h in hits)
    assert any(h.get("dst_node_id") in {"Ps.89.28", "Jer.31.33", "Job.24.19"} for h in hits)
