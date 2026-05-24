"""Atom gloss decode smoke."""

from __future__ import annotations


def test_gloss_report_ok():
    from scripts.build_mkm_inter_agent_atom_gloss_decode_v1 import run_report

    doc = run_report()
    assert doc.get("ok")
    assert "lexicon_dense" in (doc.get("samples") or {})
    dense = doc["samples"]["lexicon_dense"]
    assert dense.get("atom_id_count", 0) >= 1
    assert dense.get("gloss_text")
