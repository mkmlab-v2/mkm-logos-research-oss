"""M28: RQ-019 language-dev lane closeout pack."""

from __future__ import annotations


def test_language_dev_closeout():
    from scripts.build_mkm_inter_agent_rq019_language_dev_closeout_v1 import build_closeout

    doc = build_closeout()
    assert doc.get("ok")
    assert doc.get("language_dev_lane", {}).get("m12_m27_ready") is True
    assert "operator_runbook" in doc
    assert doc.get("research_only") is True


def test_ops_slice_m27_readiness_fields():
    from scripts.build_mkm_inter_agent_rq019_ops_slice_v1 import build_ops_slice

    doc = build_ops_slice()
    assert doc.get("ok")
    ready = doc.get("readiness") or {}
    assert ready.get("language_dev_m12_m27_ready") is True
