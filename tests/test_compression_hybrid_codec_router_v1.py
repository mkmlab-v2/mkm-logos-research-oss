"""compression_hybrid_codec_router_v1 — lib + v2 stub wiring [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.compression_hybrid_codec_router_v1_lib import (  # noqa: E402
    HYBRID_CODEC_JACCARD_FLOOR,
    has_assistant_turn,
    resolve_hybrid_codec_plan,
    select_profile_assistant_literal,
    select_profile_turns_gte,
    turn_count,
)
from scripts.compression_token_api_v2_stub import app  # noqa: E402
from scripts.report_multilens_performance_eval import _jaccard  # noqa: E402

CORPUS = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
OVERLAY = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"
client = TestClient(app)


def _wtt_request_body(row: dict) -> dict:
    from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms
    from scripts.compression_b2b_off_the_shelf_shard_sku_v1_lib import build_sku_context

    overlay = load_overlay_terms(OVERLAY) if OVERLAY.is_file() else []
    sku_ctx = build_sku_context(
        workspace_root=ROOT,
        spec_path=ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json",
        external_sku="MKM-CHAT-D1",
        shard_json_override=None,
    )
    forced = sku_ctx.get("forced_shard_id") or sku_ctx.get("override_shard_id")
    return {
        "text": row["text"],
        "loss_profile": "semantic_general",
        "compression_profile": "economy",
        "client_request_id": row["id"],
        "stateless_packet": True,
        "session_turns": row.get("turns"),
        "must_keep_overlay_terms": overlay or None,
        "forced_shard_id": forced,
    }


def _load_case(case_suffix: str) -> dict:
    needle = f"customer-v1-{case_suffix}"
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if needle in str(obj.get("id", "")):
            return obj
    raise KeyError(case_suffix)


def _compress_expand(body: dict) -> dict:
    cr = client.post("/v2/compress", json=body)
    assert cr.status_code == 200, cr.text
    pkt = cr.json()["compression_packet"]
    er = client.post("/v2/expand", json={"compression_packet": pkt, "decode_mode": "codebook_only"})
    assert er.status_code == 200, er.text
    return {"compress": cr.json(), "expand": er.json()}


def test_lib_turn_and_assistant_routes() -> None:
    multi = {
        "turns": [
            {"role": "user", "text": "a"},
            {"role": "assistant", "text": "b"},
            {"role": "user", "text": "c"},
        ]
    }
    short = {"turns": [{"role": "user", "text": "a"}, {"role": "user", "text": "b"}]}
    assert turn_count(multi["turns"]) == 3
    assert select_profile_turns_gte(multi["turns"], min_turns=3)[0] == "literal"
    assert select_profile_assistant_literal(short["turns"])[0] == "economy"


def test_resolve_plan_router_off_unchanged() -> None:
    plan = resolve_hybrid_codec_plan(
        router="off",
        session_turns=None,
        requested_profile="economy",
        short_context_token_threshold=25,
        short_context_max_saving_rate=0.15,
    )
    assert plan["effective_profile"] == "economy"
    assert plan["router"] == "off"
    assert plan["research_only"] is False


def test_health_lists_hybrid_router_modes() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "assistant_literal" in body.get("hybrid_codec_router_modes", [])
    assert body.get("hybrid_codec_router_default") == "off"


@pytest.mark.parametrize("case_suffix", ["000", "017"])
def test_stub_economy_fallback_passes_multiturn_remainder(case_suffix: str) -> None:
    row = _load_case(case_suffix)
    body = {**_wtt_request_body(row), "hybrid_codec_router": "economy_fallback"}
    out = _compress_expand(body)
    flags = out["compress"]["integrity_flags"]
    expanded = out["expand"]["text"]
    jac = float(_jaccard(row["text"], expanded))
    assert jac >= HYBRID_CODEC_JACCARD_FLOOR
    assert flags.get("hybrid_codec_research_only") is True
    if case_suffix in {"000", "017"}:
        assert flags.get("hybrid_codec_fallback_used") is True


@pytest.mark.parametrize("case_suffix", ["006", "019"])
def test_stub_assistant_literal_passes_user_only_cases(case_suffix: str) -> None:
    row = _load_case(case_suffix)
    body = {**_wtt_request_body(row), "hybrid_codec_router": "assistant_literal"}
    out = _compress_expand(body)
    flags = out["compress"]["integrity_flags"]
    expanded = out["expand"]["text"]
    jac = float(_jaccard(row["text"], expanded))
    assert jac >= HYBRID_CODEC_JACCARD_FLOOR
    assert flags.get("compression_profile_effective") == "economy"
    assert flags.get("hybrid_codec_route_reason") == "economy_default"


def test_stub_assistant_literal_routes_000_to_literal() -> None:
    row = _load_case("000")
    body = {**_wtt_request_body(row), "hybrid_codec_router": "assistant_literal"}
    out = _compress_expand(body)
    flags = out["compress"]["integrity_flags"]
    assert flags.get("compression_profile_effective") == "literal"
    assert flags.get("hybrid_codec_route_reason") == "has_assistant_turn"
