"""M15 batch session export + wire+gloss report smoke."""

from __future__ import annotations


def test_wire_sessions_batch_all_scenarios():
    from scripts.export_mkm_inter_agent_wire_sessions_batch_v1 import export_batch

    doc = export_batch(scenarios=("trading",), turns=2)
    assert doc.get("ok") is True
    assert doc.get("total_envelopes") == 2
    assert "trading" in (doc.get("sessions") or {})


def test_wire_gloss_session_report():
    from scripts.build_mkm_inter_agent_wire_gloss_session_report_v1 import build_report

    doc = build_report(turns=2, run_batch_if_missing=True)
    assert doc.get("ok") is True
    assert "trading" in (doc.get("scenario_summary") or {})
    assert "turns_by_scenario" in doc
