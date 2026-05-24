"""M18 KO tokenization experiment + health sidecar wire demo."""

from __future__ import annotations


def test_ko_tokenization_experiment():
    from scripts.build_mkm_inter_agent_ko_tokenization_experiment_v1 import run_experiment

    doc = run_experiment()
    assert doc.get("ok") is True
    assert "hangul_syllable" in (doc.get("modes") or {})


def test_health_sidecar_wire_demo_uplift():
    from scripts.run_mkm_inter_agent_ko_health_sidecar_wire_demo_v1 import run_demo

    doc = run_demo()
    assert doc.get("ok") is True
    agg = doc.get("aggregate") or {}
    assert agg.get("merged_atom_count", 0) > agg.get("baseline_wire_atom_count", 0)
