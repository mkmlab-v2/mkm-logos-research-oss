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


def test_router_matches_finance_keywords() -> None:
    router = DomainSpecificRouter(SHARDS)
    route = router.route("risk drawdown leverage control")
    assert route.shard_id == "zone_e_finance"
