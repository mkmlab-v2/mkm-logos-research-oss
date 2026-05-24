"""M19 KO health sidecar opt-in research encode."""

from __future__ import annotations

HEALTH = "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈 Silver Tech."


def test_encode_sidecar_uplift():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    c = TestClient(app)
    b = c.post("/v1/research/mkm_lexicon_wire/encode", json={"text": HEALTH, "zstd_min_raw_bytes": 0})
    s = c.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": HEALTH, "zstd_min_raw_bytes": 0, "use_ko_health_sidecar": True},
    )
    assert b.status_code == 200 and s.status_code == 200
    assert len(s.json()["atom_id_sequence"]) > len(b.json()["atom_id_sequence"])
    assert s.json()["integrity_flags"].get("ko_health_sidecar") is True


def test_wire_turn_sidecar_flag():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    r = TestClient(app).post(
        "/v1/research/mkm_inter_agent_wire/turn",
        json={"text": HEALTH, "use_ko_health_sidecar": True},
    )
    assert r.status_code == 200
    env = r.json().get("envelope") or {}
    assert (env.get("payload") or {}).get("atom_id_count", 0) > 1
