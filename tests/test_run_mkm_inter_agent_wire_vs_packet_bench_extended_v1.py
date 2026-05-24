"""M14 extended wire vs packet bench smoke."""

from __future__ import annotations


def test_extended_bench_ok():
    from scripts.run_mkm_inter_agent_wire_vs_packet_bench_extended_v1 import run_extended_bench

    doc = run_extended_bench()
    assert doc.get("ok") is True
    assert doc.get("total_unique_lines", 0) >= 6
    assert "trading" in (doc.get("corpora") or {})
