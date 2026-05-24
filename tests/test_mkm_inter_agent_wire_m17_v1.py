"""M17 KO health lexicon coverage + JSONL round-trip audit."""

from __future__ import annotations


def test_ko_health_lexicon_coverage_spike():
    from scripts.build_mkm_inter_agent_ko_health_lexicon_coverage_v1 import run_coverage

    doc = run_coverage()
    assert doc.get("ok") is True
    assert doc.get("corpus_line_count", 0) >= 4
    agg = doc.get("aggregate") or {}
    assert agg.get("token_count", 0) > 0


def test_jsonl_roundtrip_audit():
    from pathlib import Path

    from scripts.audit_mkm_inter_agent_wire_session_jsonl_roundtrip_v1 import audit_jsonl

    doc = audit_jsonl(
        Path("docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.jsonl"),
        run_batch_if_missing=True,
    )
    assert doc.get("ok") is True
    assert doc.get("line_count", 0) >= 6
    assert doc.get("all_schema_valid") is True
