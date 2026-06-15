"""v2 Trust Packet compression API stub (FastAPI).

Phase 2: V2-only compress → expand (no ``original_text`` on expand) and lock Jaccard(original, expanded)
to the same token multiset definition as ``report_multilens_performance_eval.evaluate_report`` (``_jaccard``).
Floor 0.73 aligns with Track A reconstruction fidelity targets cited in ops briefs; curated sample below
typically scores at or near 1.0 when the engine returns full ``reconstructed_text_effective``.
"""

from __future__ import annotations

import copy
from pathlib import Path

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
from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path
from scripts.report_multilens_performance_eval import _jaccard

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
OPENAPI_V2 = ROOT / "docs" / "final" / "openapi_token_compression_v2_draft.yaml"

# Track A-style floor for V2 API round-trip fidelity (original vs expand output, not v1 echo).
V2_ROUNDTRIP_JACCARD_MIN = 0.73


def test_openapi_v2_contract_has_emit_semantic_pointer() -> None:
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_V2.read_text(encoding="utf-8"))
    req = spec.get("components", {}).get("schemas", {}).get("CompressRequestV2", {})
    props = req.get("properties", {})
    assert "emit_semantic_pointer" in props
    em = props["emit_semantic_pointer"]
    assert em.get("type") == "boolean"


def test_openapi_v2_contract_has_graph_wire_selective_bridge() -> None:
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_V2.read_text(encoding="utf-8"))
    props = spec["components"]["schemas"]["CompressRequestV2"]["properties"]
    gw = props["graph_wire_selective_bridge"]
    assert gw.get("type") == "boolean"
    assert gw.get("default") is False


def test_openapi_v2_contract_has_compression_profile() -> None:
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_V2.read_text(encoding="utf-8"))
    props = spec["components"]["schemas"]["CompressRequestV2"]["properties"]
    cp = props["compression_profile"]
    assert cp.get("default") == "economy"
    assert set(cp.get("enum", [])) == {"economy", "fidelity", "literal"}


def test_openapi_v2_contract_has_corpus_tag_and_sku_class() -> None:
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_V2.read_text(encoding="utf-8"))
    props = spec["components"]["schemas"]["CompressRequestV2"]["properties"]
    assert "corpus_tag" in props
    assert props["sku_class"]["enum"] == ["coord", "mask"]


def test_compress_forced_shard_id_b2b_catalog() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "zzqv nomatch token",
            "loss_profile": "semantic_general",
            "forced_shard_id": "zone_g_health_b2b_v1",
            "client_request_id": "test-v2-forced-b2b",
        },
    )
    assert cr.status_code == 200
    pkt = cr.json()["compression_packet"]
    assert pkt["router_meta"]["shard_id"] == "zone_g_health_b2b_v1"
    assert cr.json()["integrity_flags"].get("forced_shard_id") == "zone_g_health_b2b_v1"


def test_compress_corpus_tag_public_open_web_applies_binding() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "public open web corpus sample for hybrid router binding",
            "loss_profile": "semantic_general",
            "corpus_tag": "public-open-web-v1",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("corpus_tag") == "public-open-web-v1"
    assert flags.get("hybrid_router_backend_recommended") == "mkm_candidate_pool"
    assert flags.get("hybrid_router_stub_applies_mkm") is True
    assert flags.get("routing_profile_binding") == "candidate_pool_on"
    assert flags.get("enable_candidate_pool_expansion_binding") is True
    assert flags.get("sku_class") == "mask"


def test_compress_corpus_tag_wtt_applies_shortcap_and_overlay() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "WTT premium CS customer short context sample",
            "loss_profile": "semantic_general",
            "corpus_tag": "wtt-premium-cs-customer-v1",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("corpus_tag") == "wtt-premium-cs-customer-v1"
    assert flags.get("hybrid_router_backend_recommended") == "mkm_v2_economy_shortcap"
    assert flags.get("short_context_token_threshold") == 30
    assert flags.get("short_context_max_saving_rate") == 0.3
    assert "must_keep_overlay_json" in flags


def test_compress_corpus_tag_golden40_external_backend_422() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "golden40 internal regression lane",
            "loss_profile": "semantic_general",
            "corpus_tag": "golden40_internal",
        },
    )
    assert cr.status_code == 422
    detail = cr.json()["detail"]
    assert detail["error"] == "hybrid_router_external_backend"
    assert detail["recommended_backend"] == "llmlingua2"


def test_compress_unknown_corpus_tag_422() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "unknown tag sample",
            "loss_profile": "semantic_general",
            "corpus_tag": "no-such-corpus-v99",
        },
    )
    assert cr.status_code == 422
    assert cr.json()["detail"]["error"] == "unknown_corpus_tag"


def test_compress_must_keep_overlay_terms_flag() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "공급망 SCM BOM 리드타임 재고 PoC",
            "loss_profile": "semantic_general",
            "forced_shard_id": "zone_a_scm_b2b_v1",
            "must_keep_overlay_terms": ["BOM", "리드타임", "공급망"],
            "client_request_id": "test-v2-overlay-mk",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("must_keep_overlay_terms_count") == 3


def test_compress_short_context_cap_policy_flag() -> None:
    sample = "공급망 SCM BOM 리드타임 재고 안전분 policy 범위"
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "forced_shard_id": "zone_a_scm_b2b_v1",
            "short_context_token_threshold": 40,
            "short_context_max_saving_rate": 0.35,
            "client_request_id": "test-v2-short-cap",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("short_context_token_threshold") == 40
    assert flags.get("short_context_policy_applied") is True


def test_compress_forced_shard_id_unknown_422() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "sample",
            "loss_profile": "semantic_general",
            "forced_shard_id": "zone_no_such_shard_xyz",
        },
    )
    assert cr.status_code == 422


def test_openapi_v2_contract_has_stateless_packet_and_codebook_only() -> None:
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(OPENAPI_V2.read_text(encoding="utf-8"))
    compress_props = spec["components"]["schemas"]["CompressRequestV2"]["properties"]
    assert compress_props["stateless_packet"]["default"] is False
    expand_props = spec["components"]["schemas"]["ExpandRequestV2"]["properties"]
    assert "codebook_only" in expand_props["decode_mode"]["enum"]


def test_health_v2():
    before = _legacy_flat_key_access_count()
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("compression_profiles") == ["economy", "fidelity", "literal"]
    assert j.get("compression_profile_default") == "economy"
    assert "comp_4d_anchor_ssot_v1.json" in str(j.get("anchor_ssot", ""))
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


def _packet_without_reconstructed_text(packet: dict) -> dict:
    """Trust Packet Stateless Profile: strip full-text leak; keep allowed structured residual."""
    out = copy.deepcopy(packet)
    meta = out.get("residual_meta")
    if not isinstance(meta, dict):
        return out
    stub = meta.get(RESIDUAL_STUB_KEY)
    if isinstance(stub, dict):
        slim = {k: v for k, v in stub.items() if k != "reconstructed_text"}
        out["residual_meta"] = {**meta, RESIDUAL_STUB_KEY: slim}
    return out


def test_v2_stateless_trust_packet_roundtrip_red():
    """Trust Packet Stateless Profile (DoD ②) — Step B GREEN target; RED until codebook_only exists.

    Packet diet: no mk_stub_v2.reconstructed_text; expand via decode_mode=codebook_only only.
    Must not use stub residual reassembly or degraded_compressed_text_only as the final path.
    """
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "client_request_id": "test-v2-stateless-red",
        },
    )
    assert cr.status_code == 200
    pkt_raw = cr.json()["compression_packet"]
    assert "reconstructed_text" in pkt_raw["residual_meta"][RESIDUAL_STUB_KEY]

    pkt = _packet_without_reconstructed_text(pkt_raw)
    assert "reconstructed_text" not in pkt["residual_meta"][RESIDUAL_STUB_KEY]
    assert pkt.get("compressed_text")
    assert pkt.get("router_meta", {}).get("shard_id")

    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    assert er.status_code == 200, er.text
    ej = er.json()
    flags = ej.get("integrity_flags") or {}
    assert flags.get("source") != RESIDUAL_STUB_KEY
    assert flags.get("reassembly") == "codebook_only"
    expanded = ej["text"]
    jac = _jaccard(sample, expanded)
    assert jac >= V2_ROUNDTRIP_JACCARD_MIN


def test_v2_stateless_packet_compress_and_codebook_only_roundtrip():
    """End-to-end Trust Packet Stateless Profile: compress omits reconstructed_text."""
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "client_request_id": "test-v2-stateless-e2e",
            "stateless_packet": True,
        },
    )
    assert cr.status_code == 200
    assert cr.json()["integrity_flags"].get("stateless_packet") is True
    pkt = cr.json()["compression_packet"]
    stub = pkt["residual_meta"][RESIDUAL_STUB_KEY]
    assert "reconstructed_text" not in stub

    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    assert er.status_code == 200
    flags = er.json().get("integrity_flags") or {}
    assert flags.get("reassembly") == "codebook_only"
    assert flags.get("source") != RESIDUAL_STUB_KEY
    jac = _jaccard(sample, er.json()["text"])
    assert jac >= V2_ROUNDTRIP_JACCARD_MIN


def test_v2_stateless_lossless_hybrid_codebook_only_exact():
    """Stateless packet + lossless_text: expand via codebook_only must restore hybrid payload exactly."""
    sample = "OPS gateway 8788 and SHA256 checksum must restore exactly."
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "lossless_text",
            "client_request_id": "test-v2-stateless-lossless",
            "stateless_packet": True,
        },
    )
    assert cr.status_code == 200
    assert cr.json()["integrity_flags"].get("hybrid_codec_v0_exact_restore_ok") is True
    pkt = cr.json()["compression_packet"]
    stub = pkt["residual_meta"][RESIDUAL_STUB_KEY]
    assert "reconstructed_text" not in stub
    assert "hybrid_codec_v0_payload" in stub

    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    assert er.status_code == 200
    flags = er.json().get("integrity_flags") or {}
    assert flags.get("reassembly") == "codebook_only"
    assert flags.get("source") == "hybrid_codec_v0_payload"
    assert er.json()["text"] == sample


def test_v2_stateless_stub_fallback_is_degraded_not_dod_compliant():
    """Baseline: default stub expand without reconstructed_text uses degraded path (not DoD ②)."""
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    pkt = _packet_without_reconstructed_text(cr.json()["compression_packet"])
    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "stub"},
    )
    assert er.status_code == 200
    flags = er.json().get("integrity_flags") or {}
    assert flags.get("reassembly") == "degraded_compressed_text_only"
    assert flags.get("source") != RESIDUAL_STUB_KEY


def test_v2_compress_no_force_shard_id_none_string():
    """Regression: str(None) must not become shard_id 'None' in evaluate_report."""
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    flags = cr.json().get("integrity_flags") or {}
    assert flags.get("evaluate_report_failed") is not True
    assert flags.get("error_class") != "ValueError"
    assert cr.json().get("compression_metrics") is not None


def test_v2_compress_emit_semantic_pointer_in_residual():
    sample = "사상의학 체질 분류 예시 텍스트입니다. sasang myeongri bible reference."
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "emit_semantic_pointer": True,
        },
    )
    assert cr.status_code == 200
    stub = cr.json()["compression_packet"]["residual_meta"][RESIDUAL_STUB_KEY]
    assert isinstance(stub.get("semantic_pointer"), dict)
    assert stub["semantic_pointer"].get("schema") == "semantic_pointer_v1"


@pytest.mark.slow
def test_v2_expand_l1_experimental_mode_research_only():
    """L1 beam on compressed_text only — not default stub path; research_only flags."""
    sample = "오늘 팀이 BTCUSDT 신호를 보수적으로 분석했다"
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    pkt = cr.json()["compression_packet"]
    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "l1_experimental"},
    )
    assert er.status_code == 200
    ej = er.json()
    assert ej.get("decode_mode") == "l1_experimental"
    flags = ej.get("integrity_flags") or {}
    assert flags.get("research_only") is True
    assert flags.get("decode_mode") == "l1_experimental"
    assert flags.get("reassembly") == "l1_experimental_beam"
    assert isinstance(ej.get("text"), str) and ej["text"]


def test_v2_compress_attaches_lexicon_rail_atom_ids():
    """Trust packet may carry ordered 41k atom_id sequence (MKM language vocabulary rail)."""
    sample = "MKM inter-agent rail demo strong morph bible logos reference."
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    rail = (cr.json()["compression_packet"].get("residual_meta") or {}).get("mkm_lexicon_rail_v1")
    assert isinstance(rail, dict), "expected mkm_lexicon_rail_v1 on packet"
    seq = rail.get("atom_id_sequence")
    assert isinstance(seq, list) and len(seq) >= 1
    assert rail.get("symbol_key") == "atom_id"
    assert all(isinstance(x, str) and x for x in seq)


def test_v2_mkm_lexicon_wire_encode_decode_roundtrip():
    sample = "strong morph greek logos bible reference message kai mercy alpha beta"
    enc = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": sample, "zstd_min_raw_bytes": 0},
    )
    assert enc.status_code == 200
    ej = enc.json()
    assert ej.get("integrity_flags", {}).get("research_only") is True
    assert ej.get("wire_byte_len", 0) > 0
    seq = ej.get("atom_id_sequence") or []
    assert len(seq) >= 1
    dec = client.post("/v1/research/mkm_lexicon_wire/decode", json={"wire_b64": ej["wire_b64"]})
    assert dec.status_code == 200
    assert dec.json().get("atom_id_sequence") == seq


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
    sample = "a b c d e f g"
    cr = client.post(
        "/v2/compress",
        json={"text": sample, "loss_profile": "semantic_general"},
    )
    assert cr.status_code == 200
    assert cr.json()["integrity_flags"].get("jaccard_trust_restoration") is True


def test_v2_compression_profile_fidelity_enables_bridge_policy() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "compression profile fidelity lane sample sasang",
            "loss_profile": "semantic_general",
            "compression_profile": "fidelity",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("compression_profile") == "fidelity"
    assert flags.get("apply_gematria_4d_bridge_policy") is True
    assert flags.get("apply_gematria_4d_bridge_policy_effective") is True


def test_v2_compression_profile_economy_disables_bridge_policy() -> None:
    cr = client.post(
        "/v2/compress",
        json={
            "text": "compression profile economy lane sample",
            "loss_profile": "semantic_general",
            "compression_profile": "economy",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("compression_profile") == "economy"
    assert flags.get("apply_gematria_4d_bridge_policy") is False
    assert flags.get("apply_gematria_4d_bridge_policy_effective") is False


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


def test_v2_compress_zone_f_code_forced_shard_twin_metrics() -> None:
    sample = "def api_endpoint() -> dict:\n    return {\"schema\": \"v1\", \"json\": True}"
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "forced_shard_id": "zone_f_code",
            "client_request_id": "test-v2-zone-f-code-twin",
        },
    )
    assert cr.status_code == 200
    flags = cr.json()["integrity_flags"]
    assert flags.get("forced_shard_id") == "zone_f_code"
    er = client.post("/v2/expand", json={"compression_packet": cr.json()["compression_packet"]})
    assert er.status_code == 200
    expanded = er.json()["text"]
    assert "jaccard_proxy" in flags or "jaccard_proxy" in er.json().get("integrity_flags", {})


def test_resolve_latest_codebook_uses_production_pointer() -> None:
    """v2 lexicon rail resolves production SSOT via bench pointer, not highest glob only."""
    pointer = (
        Path(__file__).resolve().parents[1]
        / "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json"
    )
    assert pointer.is_file(), "bench lexicon pointer missing"
    import json

    prod_path = json.loads(pointer.read_text(encoding="utf-8"))["production_ssot"]["path"]
    p = resolve_latest_codebook_path()
    assert p is not None
    assert p.name == Path(prod_path).name
