"""v2 Trust Packet compression API stub (FastAPI).

Phase 2: V2-only compress → expand (no ``original_text`` on expand) and lock Jaccard(original, expanded)
to the same token multiset definition as ``report_multilens_performance_eval.evaluate_report`` (``_jaccard``).
Floor 0.73 aligns with Track A reconstruction fidelity targets cited in ops briefs; curated sample below
typically scores at or near 1.0 when the engine returns full ``reconstructed_text_effective``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from scripts.compression_token_api_v2_stub import (
    API_CONTRACT_VERSION,
    PACKET_FORMAT_VERSION,
    RESIDUAL_STUB_KEY,
    _legacy_flat_key_access_count,
    _tracka_profile_deprecations,
    _tracka_profile_label,
    _tracka_profile_meta,
    _tracka_profile_override_env,
    _tracka_profile_source,
    app,
)
from scripts.tracka_profile_client_utils import extract_tracka_profile_meta
from scripts.report_multilens_performance_eval import _jaccard

client = TestClient(app)

# Track A-style floor for V2 API round-trip fidelity (original vs expand output, not v1 echo).
V2_ROUNDTRIP_JACCARD_MIN = 0.73


def test_health_v2():
    before = _legacy_flat_key_access_count()
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("api_contract_version") == API_CONTRACT_VERSION
    assert j.get("packet_format_version") == PACKET_FORMAT_VERSION
    assert j.get("tracka_profile_meta") == _tracka_profile_meta()
    assert j.get("tracka_profile_deprecations") == _tracka_profile_deprecations()
    assert "tracka_profile" not in j
    assert "tracka_profile_source" not in j
    assert "tracka_profile_override_env" not in j
    assert j.get("legacy_flat_key_access_count") == before


def test_health_and_compress_tracka_profile_consistent():
    health = client.get("/health")
    assert health.status_code == 200
    health_meta = health.json().get("tracka_profile_meta")
    assert isinstance(health_meta, dict) and health_meta

    cr = client.post(
        "/v2/compress",
        json={"text": "profile consistency check sample", "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    compress_meta = cr.json().get("integrity_flags", {}).get("tracka_profile_meta")
    compress_deprecations = cr.json().get("integrity_flags", {}).get("tracka_profile_deprecations")
    assert compress_meta == health_meta
    assert compress_deprecations == health.json().get("tracka_profile_deprecations")
    assert "tracka_profile" not in cr.json().get("integrity_flags", {})
    assert "tracka_profile_source" not in cr.json().get("integrity_flags", {})
    assert "tracka_profile_override_env" not in cr.json().get("integrity_flags", {})


def test_extract_tracka_profile_meta_prefers_meta_then_legacy_fallback():
    full = {
        "tracka_profile": "legacy_profile",
        "tracka_profile_source": "legacy_source",
        "tracka_profile_override_env": {"legacy": "yes"},
        "tracka_profile_meta": {
            "profile": "meta_profile",
            "source": "meta_source",
            "override_env": {"meta": "yes"},
        },
    }
    got_full = extract_tracka_profile_meta(full)
    assert got_full == {
        "profile": "meta_profile",
        "source": "meta_source",
        "override_env": {"meta": "yes"},
    }

    legacy_only = {
        "tracka_profile": "legacy_profile",
        "tracka_profile_source": "legacy_source",
        "tracka_profile_override_env": {"legacy": "yes"},
    }
    got_legacy = extract_tracka_profile_meta(legacy_only)
    assert got_legacy == {
        "profile": "legacy_profile",
        "source": "legacy_source",
        "override_env": {"legacy": "yes"},
    }


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
    assert cj["integrity_flags"].get("tracka_profile_meta") == _tracka_profile_meta()
    assert "tracka_profile" not in cj["integrity_flags"]
    assert "tracka_profile_source" not in cj["integrity_flags"]
    assert "tracka_profile_override_env" not in cj["integrity_flags"]
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


# Curated edge cases: empty/whitespace, ASCII, punctuation-heavy, CJK brackets, and a string that
# previously yielded sub-floor engine Jaccard (restored via Trust-Restoration in the stub).
@pytest.mark.parametrize(
    "sample",
    [
        "",
        "   \n\t",
        "a",
        "!@#$%^&*()[]",
        "한",
        "「test」 x",
        "사상의학 체질 · sasang — reference",
    ],
)
def test_v2_roundtrip_jaccard_edge_cases_min(sample: str):
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
    assert jac >= V2_ROUNDTRIP_JACCARD_MIN, f"jaccard={jac} < {V2_ROUNDTRIP_JACCARD_MIN} sample={sample!r}"


def test_v2_trust_restoration_flag_on_subfloor_engine_jaccard():
    """Engine-only reconstruction can dip below the floor; stub must restore and surface the flag."""
    sample = "「test」 x"
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    assert cr.json()["integrity_flags"].get("jaccard_trust_restoration") is True


def test_v2_lossless_profile_uses_fused_hybrid_codec():
    sample = "OPS gateway 8788 and SHA256 checksum must restore exactly."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "lossless_text"},
    )
    assert cr.status_code == 200
    cj = cr.json()
    assert cj["integrity_flags"].get("tracka_profile_meta") == _tracka_profile_meta()
    assert "tracka_profile" not in cj["integrity_flags"]
    assert "tracka_profile_source" not in cj["integrity_flags"]
    assert "tracka_profile_override_env" not in cj["integrity_flags"]
    assert cj["integrity_flags"].get("hybrid_codec_v0_fused") is True
    assert cj["integrity_flags"].get("hybrid_codec_v0_exact_restore_ok") is True

    pkt = cj["compression_packet"]
    stub = pkt["residual_meta"][RESIDUAL_STUB_KEY]
    assert "hybrid_codec_v0_payload" in stub

    er = client.post("/v2/expand", json={"compression_packet": pkt})
    assert er.status_code == 200
    assert er.json()["text"] == sample
