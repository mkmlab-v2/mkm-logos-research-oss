"""SKU-COORD vs SKU-MASK separation + hybrid router spec + moat factcheck SSOT."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTCHECK = ROOT / "docs/final/artifacts/ltm_moat_factcheck_v1_latest.json"
HYBRID_SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"
B2B_SPEC = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"
SPIKE = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_moat_factcheck_schema_and_verdict() -> None:
    doc = _load(FACTCHECK)
    assert doc["schema"] == "mkm_ltm_moat_factcheck_v1"
    assert doc["verdict"] == "CONDITIONAL_COST_MOAT_ONLY"
    assert doc["track_a_active_untouched"] is True
    assert doc["send_gate"] == "HOLD"
    assert len(doc.get("attest_matrix") or []) >= 8
    assert len(doc.get("forbidden_headlines") or []) >= 5
    assert "SKU-COORD" in doc.get("sku_separation", {})
    assert "SKU-MASK" in doc.get("sku_separation", {})


def test_hybrid_spec_bindings_match_spike_routes() -> None:
    spec = _load(HYBRID_SPEC)
    spike = _load(SPIKE)
    spec_ids = {b["corpus_id"] for b in spec["corpus_bindings"]}
    spike_routes = {r["corpus_id"]: r["backend"] for r in spike["routing_policy"]["routes"]}
    for cid, backend in spike_routes.items():
        assert cid in spec_ids
        row = next(b for b in spec["corpus_bindings"] if b["corpus_id"] == cid)
        if backend == "llmlingua2":
            assert row["backend"] == "llmlingua2"
        elif backend == "mkm_economy_shortcap":
            assert row["backend"] == "mkm_v2_economy_shortcap"
        elif backend == "mkm_candidate_pool":
            assert row["backend"] == "mkm_candidate_pool"
        else:
            assert row["backend"].startswith("mkm_v2") or row["backend"] == "mkm_candidate_pool"


def test_b2b_spec_has_sku_classes_and_hybrid_pointer() -> None:
    doc = _load(B2B_SPEC)
    assert "sku_classes" in doc
    assert doc["sku_classes"]["SKU-COORD"]["sku_class"] == "coord"
    assert doc["sku_classes"]["SKU-MASK"]["sku_class"] == "mask"
    assert doc["hybrid_router_spec"] == "docs/final/artifacts/compression_hybrid_router_spec_v1.json"
    assert len(doc["skus"]) == 4


def test_hybrid_spec_binding_table_hash_stable() -> None:
    """Regression pin: corpus_id + backend pairs."""
    spec = _load(HYBRID_SPEC)
    pairs = sorted((b["corpus_id"], b["backend"]) for b in spec["corpus_bindings"])
    digest = hashlib.sha256(json.dumps(pairs).encode()).hexdigest()[:16]
    assert digest == "e541654869d74212"


def test_hybrid_spec_v2_stub_binding_status_partial() -> None:
    spec = _load(HYBRID_SPEC)
    assert spec.get("v2_stub_binding_status") == "partial_stub_metadata"


def test_hybrid_router_lib_resolve_public_open() -> None:
    from scripts.compression_hybrid_router_spec_v1_lib import resolve_hybrid_router

    res = resolve_hybrid_router("public-open-web-v1")
    assert res is not None
    assert res.recommended_backend == "mkm_candidate_pool"
    assert res.routing_profile == "candidate_pool_on"
    assert res.enable_candidate_pool_expansion is True
    assert res.stub_can_apply_mkm is True


def test_sync_hybrid_spec_from_spike_parity() -> None:
    from scripts.sync_compression_hybrid_router_spec_from_spike_v1 import sync_spec

    result = sync_spec(
        spike_path=SPIKE,
        spec_path=HYBRID_SPEC,
        dry_run=True,
    )
    assert result["ok"] is True
    assert result["binding_table_digest"] == "e541654869d74212"


def test_b2b_spec_mask_hybrid_router_table() -> None:
    doc = _load(B2B_SPEC)
    table = doc.get("mask_hybrid_router_table") or []
    assert len(table) >= 4
    pub = next(r for r in table if r["corpus_tag"] == "public-open-web-v1")
    assert pub["backend"] == "mkm_candidate_pool"
    assert doc.get("corpus_bindings_pointer")
    assert doc.get("sku_separation_brief")


def test_sku_separation_brief_schema() -> None:
    brief = _load(ROOT / "docs/final/artifacts/compression_sku_separation_brief_v1_latest.json")
    assert brief["schema"] == "compression_sku_separation_brief_v1"
    assert brief["track_a_active_untouched"] is True
    assert "SKU-COORD" in brief["sku_classes"]
    assert brief["sku_classes"]["SKU-MASK"]["tier_a_gate"]["excluded_from_headline"] == "open_structured_long_v1"
