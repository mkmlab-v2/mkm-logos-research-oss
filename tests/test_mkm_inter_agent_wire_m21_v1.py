"""M21 KO morphology spike (research_only)."""

from __future__ import annotations


def test_morph_tokenize_heuristic():
    from scripts.mkm_inter_agent_ko_morphology_v1 import morph_tokenize

    toks, meta = morph_tokenize("환자 건강 수면 증상 호흡", prefer="heuristic_syllable")
    assert meta["backend"] == "heuristic_syllable"
    assert len(toks) >= 4


def test_morphology_spike():
    from scripts.build_mkm_inter_agent_ko_morphology_spike_v1 import run_spike

    doc = run_spike()
    assert doc.get("ok")
    assert doc.get("backends_available")
    assert doc.get("sidecar_atom_total_primary_backend", 0) > 0
