"""M16 ops brief + wire replay API smoke."""

from __future__ import annotations


def test_ops_brief_md_from_gloss_report():
    from scripts.build_mkm_inter_agent_wire_session_ops_brief_v1 import build_brief

    doc = build_brief(run_gloss_if_missing=True)
    assert doc.get("ok") is True
    assert doc.get("scenario_count", 0) >= 1
    assert doc.get("markdown_char_len", 0) > 200


def test_wire_replay_scenario_api():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    r = client.post(
        "/v1/research/mkm_inter_agent_wire/replay",
        json={"scenario": "trading", "turns": 2},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("turn_count") == 2
    assert len(body.get("turns") or []) == 2
    assert body["turns"][0].get("gloss_text")


def test_wire_replay_envelopes_inprocess():
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session
    from scripts.mkm_inter_agent_wire_replay_v1 import replay_envelopes

    session = export_session(scenario="lexicon_dense", turns=2)
    envelopes = [row["envelope"] for row in session.get("envelopes") or []]
    out = replay_envelopes(envelopes)
    assert out.get("ok") is True
    assert out.get("turn_count") == 2
