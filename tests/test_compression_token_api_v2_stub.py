"""v2 Trust Packet compression API stub (FastAPI).

Phase 2: V2-only compress → expand (no ``original_text`` on expand) and lock Jaccard(original, expanded)
to the same token multiset definition as ``report_multilens_performance_eval.evaluate_report`` (``_jaccard``).
Floor 0.73 aligns with Track A reconstruction fidelity targets cited in ops briefs; curated sample below
typically scores at or near 1.0 when the engine returns full ``reconstructed_text_effective``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.compression_token_api_v2_stub import (
    API_CONTRACT_VERSION,
    PACKET_FORMAT_VERSION,
    RESIDUAL_STUB_KEY,
    app,
)
from scripts.report_multilens_performance_eval import _jaccard

client = TestClient(app)

# Track A-style floor for V2 API round-trip fidelity (original vs expand output, not v1 echo).
V2_ROUNDTRIP_JACCARD_MIN = 0.73


def test_health_v2():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("api_contract_version") == API_CONTRACT_VERSION
    assert j.get("packet_format_version") == PACKET_FORMAT_VERSION


def test_compress_expand_roundtrip_semantic_general():
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "client_request_id": "test-v2-rt-1",
        },
    )
    assert cr.status_code == 200
    cj = cr.json()
    pkt = cj["compression_packet"]
    assert pkt["packet_format_version"] == PACKET_FORMAT_VERSION
    assert pkt["api_contract_version"] == API_CONTRACT_VERSION
    assert pkt["loss_profile"] == "semantic_general"
    assert "compressed_text" in pkt and pkt["compressed_text"]
    assert RESIDUAL_STUB_KEY in pkt["residual_meta"]
    assert "reconstructed_text" in pkt["residual_meta"][RESIDUAL_STUB_KEY]

    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt},
    )
    assert er.status_code == 200
    ej = er.json()
    assert ej.get("api_contract_version") == API_CONTRACT_VERSION
    recon = ej["text"]
    stub_res = pkt["residual_meta"][RESIDUAL_STUB_KEY]["reconstructed_text"]
    assert recon == stub_res


def test_v2_expand_accepts_trust_packet_only():
    """Expand caller sends only ``compression_packet`` (no v1-style ``original_text`` field)."""
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    pkt = cr.json()["compression_packet"]
    body = {"compression_packet": pkt}
    assert "original_text" not in body
    er = client.post("/v2/expand", json=body)
    assert er.status_code == 200


def test_v2_roundtrip_jaccard_original_vs_expanded_min():
    """Multilens Jaccard(original, expand) after V2-only pipeline >= Track A style floor."""
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    pkt = cr.json()["compression_packet"]
    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt},
    )
    assert er.status_code == 200
    expanded = er.json()["text"]
    jac = _jaccard(sample, expanded)
    assert jac >= V2_ROUNDTRIP_JACCARD_MIN, f"jaccard={jac} < {V2_ROUNDTRIP_JACCARD_MIN}"
