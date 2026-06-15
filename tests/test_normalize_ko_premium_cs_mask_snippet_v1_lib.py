"""Canonical KO CS mask snippet normalization."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_canonicalize_compression_v1_order_id() -> None:
    from scripts.normalize_ko_premium_cs_mask_snippet_v1_lib import canonicalize_ko_cs_mask_snippet

    raw = (
        "환불 처리 관련하여 주문번호 ORD-2026-061101 환불 요청합니다. 이*민 명의 결제입니다. "
        "네, 고객님. 이*민 명의로 결제된 내역 확인 도와드리겠습니다. "
        "010-****-1234 로 연락 주세요. 대기 너무 깁니다."
    )
    canon = canonicalize_ko_cs_mask_snippet(raw)
    assert "ORD-2026" not in canon
    assert "███" in canon


def test_compression_v1_corpus_canonical_wire_match() -> None:
    from scripts.compression_ko_premium_cs_deep_pack_v1_lib import load_template_catalog
    from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import load_shard
    from scripts.zone_ko_premium_cs_template_catalog_coverage_v1_lib import evaluate_corpus_snippet_coverage

    corpus = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-compression-v1_v1_bodyonly_v1.jsonl"
    shard = load_shard(ROOT / "codebook/shards/zone_ko_premium_cs_v1.json")
    catalog = load_template_catalog(ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl")
    row = evaluate_corpus_snippet_coverage(
        corpus,
        shard=shard,
        catalog_rows=catalog,
    )
    assert row["snippet_candidates_total"] == 4
    assert row["wire_match_count"] == 4
    assert row["wire_match_rate"] == 1.0
    assert int(row.get("canonical_normalized_match_count") or 0) == 4


def test_icp_operator_variant_canonical_matches_kcs_t023() -> None:
    import json

    from scripts.compression_ko_premium_cs_deep_pack_v1_lib import load_template_catalog, resolve_template_match
    from scripts.normalize_ko_premium_cs_mask_snippet_v1_lib import (
        canonicalize_ko_cs_mask_snippet,
        resolve_ko_cs_catalog_match,
    )

    raw = (
        "오늘 상담 진행 건 정리 부탁드립니다. 이*민 고객 케이스요. "
        "010-****-1030 로 요약 메일 보내 주세요."
    )
    canon = canonicalize_ko_cs_mask_snippet(raw)
    catalog = load_template_catalog(ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl")
    kcs_t023 = next(r for r in catalog if r["template_id"] == "kcs_t023")
    assert canon == kcs_t023["snippet"]
    assert resolve_ko_cs_catalog_match(raw, catalog) == resolve_template_match(canon, catalog)
