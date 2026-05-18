"""v2 compress routing profiles (Track A signoff + B-track domain relax)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.compression_token_api_v2_stub import app
from scripts.compression_v2_routing_profile_v1 import routing_profile_kwargs

client = TestClient(app)


def test_routing_profile_track_a_signoff_has_ssot_override() -> None:
    kw = routing_profile_kwargs("track_a_promoted")
    overrides = kw.get("domain_relaxed_max_saving_overrides") or {}
    assert overrides.get("ssot") == 0.45
    allow = kw.get("domain_relaxed_max_saving_case_allowlist")
    assert allow is not None and "cmp2_006" in allow


def test_v2_compress_top5_case_id_gets_higher_savings_than_default() -> None:
    text = "source artifact ssot fact-lock governance policy quality review traceability"
    base = client.post(
        "/v2/compress",
        json={
            "text": text,
            "loss_profile": "semantic_general",
            "client_request_id": "cmp2_006",
            "routing_profile": "default",
        },
    )
    promoted = client.post(
        "/v2/compress",
        json={
            "text": text,
            "loss_profile": "semantic_general",
            "client_request_id": "cmp2_006",
            "routing_profile": "track_a_promoted",
        },
    )
    assert base.status_code == 200 and promoted.status_code == 200
    s0 = base.json().get("compression_metrics", {}).get("savings_ratio") or 0.0
    s1 = promoted.json().get("compression_metrics", {}).get("savings_ratio") or 0.0
    assert s1 >= s0


def test_b_track_domain_relax_flags_research_only() -> None:
    r = client.post(
        "/v2/compress",
        json={
            "text": "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 진단",
            "loss_profile": "semantic_general",
            "routing_profile": "b_track_domain_relax",
        },
    )
    assert r.status_code == 200
    flags = r.json().get("integrity_flags") or {}
    assert flags.get("routing_research_only") is True
    assert flags.get("routing_profile") == "b_track_domain_relax"
