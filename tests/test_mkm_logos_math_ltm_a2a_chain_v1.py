"""Phase 2 Logos LTM graph + A2A trust packet chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_logos_math_ltm_a2a_chain_v1_latest.json"
TRUST = ROOT / "docs/final/artifacts/logos_a2a_trust_packet_v1_latest.json"


@pytest.fixture(scope="module")
def logos_ltm_a2a_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_mkm_logos_math_ltm_a2a_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_chain_report_pass(logos_ltm_a2a_chain: None) -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["chain_pass"] is True
    assert doc["dialogue_scenario"] == "logos_math"
    assert "logos_cosmic_anchor_graph_math" in doc["logos_concept_ids"]


def test_trust_packet_wire_refs_only(logos_ltm_a2a_chain: None) -> None:
    doc = json.loads(TRUST.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_a2a_trust_packet_v1"
    refs = doc["logos_wire_refs"]
    assert len(refs["anchor_ids"]) <= 3
    assert set(refs["vector_4d"]) == {"S", "L", "K", "M"}
    assert doc["compress_result"]["decision"] == "compressed"
    assert "per_anchor" not in refs
    omit = (doc.get("wire_handoff_hint") or {}).get("omit_on_wire") or []
    assert "per_anchor" in omit


def test_ltm_graph_logos_concepts_routable(logos_ltm_a2a_chain: None) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
        CONCEPT_BY_ID,
        load_graph,
        route_concepts_by_query,
    )

    graph = load_graph(ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json")
    routed = route_concepts_by_query(graph, "logos gematria router 4d cosmic anchor")
    ids = [cid for cid, _ in routed]
    assert "logos_cosmic_anchor_graph_math" in ids
    assert CONCEPT_BY_ID["logos_router_regression_bundle"].lane_hint == "oracle"
