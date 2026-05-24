"""DF-P0-01 Graph-Wire-RAG PoC contract (LO-CG-01 honest metrics)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_mkm_graph_wire_rag_poc_v1_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_graph_wire_rag_poc_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_poc_artifact_schema_and_honest_metrics() -> None:
    path = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_graph_wire_rag_poc_v1"
    assert doc.get("policy", {}).get("research_only") is True
    assert doc.get("policy", {}).get("non_gating") is True
    wire = doc.get("wire") or {}
    wire_len = int(wire.get("wire_byte_len") or 0)
    envelope_len = int(wire.get("envelope_utf8_byte_len") or 0)
    naive_len = int(wire.get("naive_json_utf8_byte_len") or 0)
    assert wire_len > 0
    assert envelope_len > 0
    assert naive_len > 0

    hm = wire.get("honest_metrics") or {}
    for key in (
        "payload_size_ratio",
        "payload_savings_ratio",
        "governance_overhead_factor",
        "envelope_to_wire_factor",
    ):
        assert key in hm
        assert isinstance(hm[key], (int, float))

    assert 0.0 < hm["payload_size_ratio"] < 1.0
    assert 0.0 < hm["payload_savings_ratio"] < 1.0
    assert hm["governance_overhead_factor"] > 1.0
    assert hm["envelope_to_wire_factor"] > 1.0

    deprecated = wire.get("bytes_ratio_vs_naive_json")
    assert isinstance(deprecated, dict) and deprecated.get("deprecated") is True
    assert deprecated.get("value") == hm["governance_overhead_factor"]


def test_compute_honest_wire_metrics_unit() -> None:
    from scripts.build_mkm_graph_wire_rag_poc_v1 import compute_honest_wire_metrics

    hm = compute_honest_wire_metrics(177, 1481, 612)
    assert hm["payload_size_ratio"] == round(177 / 612, 4)
    assert hm["governance_overhead_factor"] == round(1481 / 612, 4)
    assert hm["payload_savings_ratio"] == round(1.0 - 177 / 612, 4)
