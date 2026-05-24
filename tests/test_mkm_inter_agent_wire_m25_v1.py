"""M25: Track C slice + sidecar-enriched gloss + wire profile flags."""

from __future__ import annotations


def test_trackc_rq019_slice():
    from scripts.build_mkm_inter_agent_trackc_rq019_slice_v1 import build_slice

    doc = build_slice()
    assert doc.get("ok")
    assert doc.get("language_dev_m12_m24_ready") is True


def test_gloss_sidecar_enriched():
    from scripts.build_mkm_inter_agent_wire_gloss_sidecar_enriched_v1 import build_enriched

    doc = build_enriched(turns=3)
    assert doc.get("ok")
    assert doc.get("sidecar_analysis", {}).get("health_session_use_sidecar") is True


def test_wire_profile_v1_sidecar_flags():
    from scripts.build_mkm_inter_agent_wire_profile_v1 import build

    doc = build()
    flags = doc.get("research_optional_flags") or {}
    assert flags.get("use_ko_health_sidecar", {}).get("default") is False
