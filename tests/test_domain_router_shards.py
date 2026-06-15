# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.6, M:0.5}
# Balance: 88
# Purpose: Validate domain shard consistency and safe router fallback.
# Keywords: test, domain_router, shards, fallback
from __future__ import annotations

import json
from pathlib import Path

from scripts.core.domain_router import DomainSpecificRouter


ROOT = Path(__file__).resolve().parent.parent
SHARDS = ROOT / "codebook" / "shards"


def test_shard_count_and_required_fields() -> None:
    files = sorted(SHARDS.glob("zone_*.json"))
    assert len(files) >= 8
    required = {"shard_id", "domain", "routing_keywords", "must_keep_hard_terms", "must_keep_soft_terms", "guard_tokens", "hangul_principle"}
    for f in files:
        payload = json.loads(f.read_text(encoding="utf-8"))
        assert required.issubset(payload.keys())


def test_router_fallback_to_ssot_default() -> None:
    router = DomainSpecificRouter(SHARDS)
    route = router.route("zzqv_x1 randomtoken nomatch")
    assert route.shard_id == "zone_d_ssot"
    assert route.domain == "ssot"


def test_router_hangul_ratio_fallback_zone_c_when_no_routing_keyword_hits() -> None:
    """Bench cmp2_012-style: Hangul-heavy but no whole-token match on routing_keywords → zone_c."""
    router = DomainSpecificRouter(SHARDS)
    raw = (
        "소음인의 피로는 겉으로 약해 보여도 속한이 동반되는 경우가 많아서 "
        "따뜻한 식사와 규칙 수면을 함께 지켜야 한다."
    )
    route = router.route(raw)
    assert route.shard_id == "zone_c_hangul"
    assert route.domain == "hangul"
    assert route.hangul_principle is True


def test_router_matches_finance_keywords() -> None:
    router = DomainSpecificRouter(SHARDS)
    route = router.route("risk drawdown leverage control")
    assert route.shard_id == "zone_e_finance"


def test_route_from_shard_id_ignores_text() -> None:
    router = DomainSpecificRouter(SHARDS)
    r = router.route_from_shard_id("zone_c_hangul")
    assert r.shard_id == "zone_c_hangul"
    assert r.domain == "hangul"


def test_route_from_shard_id_unknown_raises() -> None:
    router = DomainSpecificRouter(SHARDS)
    try:
        router.route_from_shard_id("zone_no_such_shard_xyz")
    except ValueError as e:
        assert "Unknown shard_id" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_route_from_shard_id_b2b_catalog_without_auto_keyword_route() -> None:
    router = DomainSpecificRouter(SHARDS)
    r = router.route_from_shard_id("zone_g_health_b2b_v1")
    assert r.shard_id == "zone_g_health_b2b_v1"
    assert r.domain == "health_b2b"
    # B2B shards are catalog-only for keyword scoring — auto route must not pick b2b id.
    auto = router.route("환자 임상 진단 의료 바이탈 건강검진")
    assert auto.shard_id != "zone_g_health_b2b_v1"
