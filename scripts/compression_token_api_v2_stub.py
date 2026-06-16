#!/usr/bin/env python3
"""FastAPI v2 draft: Trust Packet round-trip (openapi_token_compression_v2_draft.yaml, Fact-Lock §11).

Run: uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011

Compress uses ``evaluate_report`` (same family as v1 live hydration). The packet's ``residual_meta``
Default ``POST /v2/expand`` (``decode_mode=stub``) may read ``mk_stub_v2.reconstructed_text``.
``decode_mode=codebook_only`` is the Trust Packet Stateless Profile (no full-text residual).
``stateless_packet`` on compress omits ``reconstructed_text`` from the packet. Still experimental, not production SLA.
``GlobalPivotCompressionPipeline`` is not used; name in early drafts was superseded by this path.

Dev: MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY=1 enables full gematria/4D bridge policy in evaluate_report (see compression_token_api_stub).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from scripts.compression_hybrid_codec_router_v1_lib import (  # noqa: E402
    HYBRID_CODEC_JACCARD_FLOOR,
    HybridCodecRouter,
    hybrid_router_integrity_flags,
    resolve_hybrid_codec_plan,
)
from scripts.compression_hybrid_router_spec_v1_lib import (  # noqa: E402
    HybridRouterResolution,
    corpus_binding_integrity_flags,
    resolve_hybrid_router,
)
from scripts.en_business_shadow_router_bind_v1_lib import (  # noqa: E402
    corpus_tag_triggers_shadow,
    load_shadow_bind_spec,
    shadow_bind_integrity_flags,
)
from scripts.compression_profile_v1 import (  # noqa: E402
    CompressionProfile,
    profile_evaluate_report_kwargs_v2,
    profile_meta,
)
from scripts.compression_token_api_stub import (  # noqa: E402
    TOKEN_RE,
    _baseline_avg_jaccard,
    _decision_selected_profile,
)
from scripts.compression_v2_routing_profile_v1 import (  # noqa: E402
    RoutingProfile,
    resolve_v2_case_id,
    routing_profile_eval_kwargs,
    routing_profile_kwargs,
)
from scripts.core.domain_router import DomainSpecificRouter, ShardRoute  # noqa: E402
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_atom_sequence_for_text,
    resolve_latest_codebook_path,
)
from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy  # noqa: E402
from scripts.report_multilens_performance_eval import _jaccard, evaluate_report  # noqa: E402
from scripts.run_hybrid_codec_v0_spike import (  # noqa: E402
    decode_packet_dict as hybrid_decode_packet_dict,
)
from scripts.run_hybrid_codec_v0_spike import (  # noqa: E402
    encode_packet_dict as hybrid_encode_packet_dict,
)
from scripts.run_hybrid_codec_v0_spike import _phrase_first_enabled  # noqa: E402

API_CONTRACT_VERSION = "2.0.0-draft"
PACKET_FORMAT_VERSION = "trust_packet.0.1"
RESIDUAL_STUB_KEY = "mk_stub_v2"
LEXICON_RAIL_KEY = "mkm_lexicon_rail_v1"
LEXICON_WIRE_SCHEMA = "mkm_lexicon_wire_v1"
# Same multiset definition as tests (`_jaccard`); floor aligns with Track A round-trip targets.
V2_JACCARD_TRUST_MIN = 0.73
_LEGACY_FLAT_KEY_ACCESS_COUNT = 0

CODING_DEEP_PACK_KEY = "coding_deep_pack_wire_v1"
_TEMPLATES_PATH = ROOT / "codebook" / "templates" / "zone_f_code_templates_v1.jsonl"
_MANIFEST_PATH = ROOT / "codebook" / "templates" / "zone_f_code_templates_manifest_v1.json"

EN_BUSINESS_DEEP_PACK_KEY = "en_business_deep_pack_wire_v1"
_EB_TEMPLATES_PATH = ROOT / "codebook" / "templates" / "zone_h_en_business_templates_v1.jsonl"
_EB_MANIFEST_PATH = ROOT / "codebook" / "templates" / "zone_h_en_business_templates_manifest_v1.json"

KO_PREMIUM_CS_DEEP_PACK_KEY = "ko_premium_cs_deep_pack_wire_v1"
_KCS_TEMPLATES_PATH = ROOT / "codebook" / "templates" / "zone_ko_premium_cs_templates_v1.jsonl"
_KCS_MANIFEST_PATH = ROOT / "codebook" / "templates" / "zone_ko_premium_cs_templates_manifest_v1.json"

from scripts.compression_coding_deep_pack_v1_lib import (  # noqa: E402
    build_wire_packet,
    expand_template_wire,
    load_template_catalog,
    match_template_id_by_snippet,
    match_template_with_literal_slots,
    measure_template_wire_twin,
    resolve_template_match,
    wire_to_compact,
)

from scripts.compression_en_business_deep_pack_v1_lib import (  # noqa: E402
    build_wire_packet as eb_build_wire_packet,
    expand_template_wire as eb_expand_template_wire,
    load_template_catalog as eb_load_template_catalog,
    measure_template_wire_twin as eb_measure_template_wire_twin,
    resolve_template_match as eb_resolve_template_match,
)

from scripts.compression_ko_premium_cs_deep_pack_v1_lib import (  # noqa: E402
    build_wire_packet as kcs_build_wire_packet,
    expand_template_wire as kcs_expand_template_wire,
    load_template_catalog as kcs_load_template_catalog,
    measure_template_wire_twin as kcs_measure_template_wire_twin,
    resolve_template_match as kcs_resolve_template_match,
)

from scripts.coord_anatomy_overlay_wire_v1_lib import (  # noqa: E402
    COORD_WIRE_KEY,
    WIRE_MODE as COORD_ANATOMY_WIRE_MODE,
    compact_coord_wire,
    expand_coord_wire_to_text,
    parse_coord_wire_text,
)

SHARDS = ROOT / "codebook" / "shards"
_router = DomainSpecificRouter(SHARDS)

LossProfile = Literal["lossless_text", "semantic_general", "code_equivalent"]
SkuClass = Literal["coord", "mask"]

app = FastAPI(
    title="MKM Token Compression API v2 (Trust Packet stub)",
    version="0.1.0-draft",
)

_cors_raw = os.environ.get("COMPRESSION_API_CORS_ALLOW_ORIGINS", "*").strip()
_cors_origins = ["*"] if _cors_raw in {"", "*"} else [x.strip() for x in _cors_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompressRequestV2(BaseModel):
    text: str
    loss_profile: LossProfile
    compression_profile: CompressionProfile = "economy"
    locale: str | None = None
    client_request_id: str | None = None
    notes: str | None = None
    emit_semantic_pointer: bool = False
    graph_wire_selective_bridge: bool = False
    routing_profile: RoutingProfile = "track_a_promoted"
    stateless_packet: bool = False
    forced_shard_id: str | None = None
    corpus_tag: str | None = Field(
        default=None,
        description=(
            "Hybrid router corpus tag (research_only). Resolves backend/profile overrides from "
            "docs/final/artifacts/compression_hybrid_router_spec_v1.json."
        ),
    )
    sku_class: SkuClass | None = Field(
        default=None,
        description="Optional SKU class hint: coord (pointer/inject) or mask (masked JSONL + v2/hybrid).",
    )
    must_keep_overlay_terms: list[str] | None = Field(
        default=None,
        description="Tenant/B2B overlay terms merged into evaluate_report must_keep (research_only).",
    )
    short_context_token_threshold: int | None = Field(
        default=None,
        ge=1,
        description="When token_in_proxy <= threshold, apply short_context_max_saving_rate and optional floor disable.",
    )
    short_context_max_saving_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Cap max saving for short inputs (research B2B PoC).",
    )
    short_context_disable_min_saving_floor: bool = Field(
        default=True,
        description="When short-context policy applies, set domain min_saving_floor override to 0.",
    )
    hybrid_codec_router: HybridCodecRouter = Field(
        default="off",
        description="B-track session router [HYPO]: assistant_literal | economy_fallback.",
    )
    session_turns: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional chat turns [{role, text}] for hybrid_codec_router heuristics.",
    )
    enable_candidate_pool_expansion: bool = Field(
        default=False,
        description=(
            "B-track [HYPO]: evaluate_report candidate pool expansion (41k combo grid best arm). "
            "Also enabled via routing_profile=candidate_pool_on. research_only; not Track A ACTIVE."
        ),
    )
    enable_coding_deep_pack: bool = Field(
        default=False,
        description=(
            "B-track [HYPO]: zone_f_code template-catalog wire (ZF_MASK) when snippet matches "
            "codebook/templates/zone_f_code_templates_v1.jsonl. Also auto when sku_class=mask "
            "and routed shard is zone_f_code."
        ),
    )
    enable_en_business_deep_pack: bool = Field(
        default=False,
        description=(
            "B-track [HYPO]: zone_h_en_business formal template wire (BIZ_MASK) when snippet matches "
            "codebook/templates/zone_h_en_business_templates_v1.jsonl. Also auto when sku_class=mask "
            "and routed shard is zone_h_en_business_v1."
        ),
    )
    enable_ko_premium_cs_deep_pack: bool = Field(
        default=False,
        description=(
            "B-track [HYPO]: zone_ko_premium_cs masked CS template wire (CS_MASK) when snippet matches "
            "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl. Also auto when sku_class=mask "
            "and routed shard is zone_ko_premium_cs_v1. Mask tokens (███) must exact-restore."
        ),
    )


class CompressionPacket(BaseModel):
    packet_format_version: str = PACKET_FORMAT_VERSION
    api_contract_version: str = API_CONTRACT_VERSION
    loss_profile: LossProfile
    compressed_text: str
    residual_meta: dict[str, Any]
    router_meta: dict[str, Any] = Field(default_factory=dict)
    content_fingerprint: str | None = None


class CompressionMetricsV2(BaseModel):
    token_in: int | None = None
    token_out: int | None = None
    savings_ratio: float | None = None


class CompressResponseV2(BaseModel):
    compression_packet: CompressionPacket
    compression_metrics: CompressionMetricsV2 | None = None
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


DecodeMode = Literal["stub", "l1_experimental", "codebook_only"]


class ExpandRequestV2(BaseModel):
    compression_packet: CompressionPacket
    decode_mode: DecodeMode = "stub"


class ExpandResponseV2(BaseModel):
    text: str
    api_contract_version: str = API_CONTRACT_VERSION
    decode_mode: DecodeMode = "stub"
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class MkmLexiconWireEncodeRequest(BaseModel):
    text: str | None = None
    atom_id_sequence: list[str] | None = None
    zstd_min_raw_bytes: int = Field(default=64, ge=0)
    zstd_level: int = Field(default=3, ge=1, le=22)
    use_ko_health_sidecar: bool = Field(
        default=False,
        description="[HYPO] B-track: merge KO health sidecar atoms (research_only; not Track A).",
    )


class MkmLexiconWireEncodeResponse(BaseModel):
    schema: str = "mkm_lexicon_wire_encode_v1"
    wire_b64: str
    wire_byte_len: int
    codec_variant: str
    atom_id_sequence: list[str]
    lexicon_meta: dict[str, Any] = Field(default_factory=dict)
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class MkmLexiconWireDecodeRequest(BaseModel):
    wire_b64: str


class MkmLexiconWireDecodeResponse(BaseModel):
    schema: str = "mkm_lexicon_wire_decode_v1"
    payload: dict[str, Any]
    atom_id_sequence: list[str]
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class MkmWireTurnRequest(BaseModel):
    text: str
    session_id: str | None = None
    turn_id: int = Field(default=1, ge=1)
    from_agent: str = "agent_alpha"
    to_agent: str = "agent_beta"
    loss_profile: str = "semantic_general"
    routing_profile: str = "track_a_promoted"
    zstd_min_raw_bytes: int = Field(default=0, ge=0)
    use_ko_health_sidecar: bool = Field(default=False, description="[HYPO] B-track KO health sidecar overlay.")


class MkmWireTurnResponse(BaseModel):
    envelope_schema: str = "mkm_inter_agent_wire_envelope_v1"
    envelope: dict[str, Any]
    envelope_utf8_byte_len: int
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class MkmWireReplayRequest(BaseModel):
    envelopes: list[dict[str, Any]] | None = None
    scenario: str | None = Field(default=None, description="trading|health|lexicon_dense demo export")
    turns: int = Field(default=4, ge=2, le=16)
    use_ko_health_sidecar: bool = Field(default=False, description="[HYPO] when scenario export is used")


class MkmWireReplayResponse(BaseModel):
    schema: str = "mkm_inter_agent_wire_replay_v1"
    turn_count: int
    turns: list[dict[str, Any]]
    scenario: str | None = None
    session_id: str | None = None
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


def _token_count_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _apply_v2_trust_restoration(
    raw: str,
    compressed: str,
    reconstructed: str,
    global_ratio: float | None,
) -> tuple[str, str, float | None, float, bool]:
    """If reconstruction vs raw is below the Jaccard floor, drop aggressive compression (identity).

    Preserves API round-trip semantics for expand (reconstructed_text) while capping claimed savings.
    Returns (compressed, reconstructed, savings_ratio_or_none, jaccard_after, restored).
    """
    jac = _jaccard(raw, reconstructed)
    if jac >= V2_JACCARD_TRUST_MIN:
        return compressed, reconstructed, global_ratio, jac, False
    ratio_out = 0.0 if global_ratio is not None else None
    jac_after = _jaccard(raw, raw)
    return raw, raw, ratio_out, jac_after, True


def _stateless_codebook_jaccard_proxy(
    raw_text: str,
    ev: dict[str, Any],
    *,
    loss_profile: LossProfile,
    route: ShardRoute,
    stateless_packet: bool,
) -> float:
    """PoC-aligned pass gate: codebook_only expand Jaccard (not trust-restored stub)."""
    comp = str(ev.get("compressed_text") or raw_text)
    rec = str(ev.get("reconstructed_text") or raw_text)
    stub_block: dict[str, Any] = {
        "reconstructed_text": rec,
        "global_token_saving_rate": ev.get("global_ratio"),
        "reconstruction_fidelity_jaccard": ev.get("jaccard"),
    }
    residual_meta: dict[str, Any] = {
        RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=stateless_packet),
        "placeholder_map": {},
    }
    _attach_lexicon_rail(residual_meta, raw_text)
    pkt = CompressionPacket(
        loss_profile=loss_profile,
        compressed_text=comp,
        residual_meta=residual_meta,
        router_meta={"shard_id": route.shard_id, "domain": route.domain},
    )
    expanded, _ = _expand_codebook_only(pkt)
    return float(_jaccard(raw_text, expanded))


def _hybrid_fallback_gate_jaccard(
    raw_text: str,
    ev: dict[str, Any],
    *,
    loss_profile: LossProfile,
    route: ShardRoute,
    stateless_packet: bool,
    jac_after_trust: float | None,
) -> float:
    if stateless_packet:
        return _stateless_codebook_jaccard_proxy(
            raw_text, ev, loss_profile=loss_profile, route=route, stateless_packet=stateless_packet
        )
    return float(jac_after_trust if jac_after_trust is not None else ev.get("jaccard") or 0.0)


def _resolve_router_route(text: str, forced_shard_id: str | None) -> ShardRoute:
    sid = str(forced_shard_id or "").strip()
    if sid:
        return _router.route_from_shard_id(sid)
    return _router.route(text)


def _normalize_optional_shard_id(shard_id: str | None) -> str | None:
    if shard_id is None:
        return None
    sid = str(shard_id).strip()
    return sid or None


def _run_evaluate_for_packet(
    text: str,
    loss_profile: LossProfile,
    *,
    emit_semantic_pointer: bool = False,
    graph_wire_selective_bridge: bool = False,
    client_request_id: str | None = None,
    routing_profile: RoutingProfile = "track_a_promoted",
    compression_profile: CompressionProfile = "economy",
    force_shard_id: str | None = None,
    extra_must_keep: set[str] | None = None,
    short_context_token_threshold: int | None = None,
    short_context_max_saving_rate: float | None = None,
    short_context_disable_min_saving_floor: bool = True,
    enable_candidate_pool_expansion: bool = False,
) -> dict[str, Any]:
    """Run evaluate_report and return payload for Trust Packet fields."""
    prof_kw = profile_evaluate_report_kwargs_v2(
        compression_profile,
        graph_wire_selective_bridge=graph_wire_selective_bridge,
    )
    strategy = str(prof_kw["strategy"])
    intensity = str(prof_kw["intensity"])
    general_cap = prof_kw.get("general_max_saving_rate")
    sensitive_cap = prof_kw.get("sensitive_max_saving_rate")
    hangul_cap = prof_kw.get("hangul_max_saving_rate")
    domain_floor_overrides: dict[str, float] | None = None
    token_in = _token_count_proxy(text)
    if (
        short_context_token_threshold is not None
        and token_in <= short_context_token_threshold
    ):
        if short_context_max_saving_rate is not None:
            general_cap = sensitive_cap = hangul_cap = short_context_max_saving_rate
        if short_context_disable_min_saving_floor:
            try:
                route_pre = _resolve_router_route(text, _normalize_optional_shard_id(force_shard_id))
                domain_floor_overrides = {route_pre.domain: 0.0}
            except ValueError:
                domain_floor_overrides = {"ssot": 0.0}
    case_id = resolve_v2_case_id(client_request_id)
    t0 = perf_counter()
    doc = {
        "compression_cases": [
            {
                "id": case_id,
                "raw_text": text,
                "compressed_text": "",
                "reconstructed_text": "",
            }
        ],
        "fusion_answer_cases": [],
    }
    _bp = bool(prof_kw.get("apply_gematria_4d_bridge_policy"))
    route_kw = routing_profile_kwargs(routing_profile)
    eval_extra = dict(routing_profile_eval_kwargs(routing_profile))
    pool_flag = eval_extra.pop("enable_candidate_pool_expansion", None)
    pool_on = bool(enable_candidate_pool_expansion or pool_flag)
    if pool_on:
        eval_extra["enable_candidate_pool_expansion"] = True
    lexicon_on = eval_extra.pop("use_master_codebook_lexicon_v1", None)
    if lexicon_on is not None:
        prof_kw = dict(prof_kw)
        prof_kw["use_master_codebook_lexicon_v1"] = bool(lexicon_on)
    bridge_policy = eval_extra.pop("apply_gematria_4d_bridge_policy", None)
    if bridge_policy is not None:
        _bp = bool(bridge_policy)
    case_wire: dict[str, dict[str, Any]] | None = None
    if graph_wire_selective_bridge:
        from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: WPS433
            build_wire_influence_for_text,
        )

        inf = build_wire_influence_for_text(text, case_id=case_id)
        if inf:
            case_wire = {case_id: inf}
    must_keep_base = {"사상의학", "체질", "sasang", "myeongri", "bible"}
    if extra_must_keep:
        must_keep_base = must_keep_base | {str(t).strip() for t in extra_must_keep if str(t).strip()}
    report = evaluate_report(
        doc,
        source_input="api:v2_trust_packet",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=must_keep_base,
        jaccard_drop_threshold_pp=1.5,
        baseline_avg_jaccard=_baseline_avg_jaccard(),
        general_max_saving_rate=float(general_cap) if general_cap is not None else None,
        sensitive_max_saving_rate=float(sensitive_cap) if sensitive_cap is not None else None,
        hangul_max_saving_rate=float(hangul_cap) if hangul_cap is not None else None,
        use_domain_router=bool(prof_kw.get("use_domain_router", True)),
        use_master_codebook_lexicon_v1=bool(prof_kw.get("use_master_codebook_lexicon_v1", True)),
        include_gematria_metadata=bool(prof_kw.get("include_gematria_metadata", _bp)),
        include_gematria_4d_bridge=bool(prof_kw.get("include_gematria_4d_bridge", _bp)),
        include_cee_core=bool(prof_kw.get("include_cee_core", _bp)),
        apply_gematria_4d_bridge_policy=_bp,
        emit_semantic_pointer=emit_semantic_pointer,
        graph_wire_selective_bridge=graph_wire_selective_bridge,
        case_graph_wire_influence=case_wire,
        force_shard_id=_normalize_optional_shard_id(force_shard_id),
        domain_min_saving_floor_overrides=domain_floor_overrides,
        **eval_extra,
    )
    elapsed_ms = round((perf_counter() - t0) * 1000.0, 3)
    comp_block = report.get("compression_metrics", {})
    cases = comp_block.get("cases", [])
    if not isinstance(cases, list) or not cases:
        return {
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": "no_cases",
            "compressed_text": text,
            "reconstructed_text": text,
            "global_ratio": 0.0,
            "jaccard": None,
        }
    first = cases[0] if isinstance(cases[0], dict) else {}
    comp = str(first.get("compressed_text_effective", "") or "")
    rec = str(first.get("reconstructed_text_effective", "") or "")
    ratio = float(comp_block.get("global_token_saving_rate", 0.0))
    jac = first.get("reconstruction_fidelity_jaccard")
    sp_first: dict[str, Any] | None = None
    if emit_semantic_pointer:
        cand = first.get("semantic_pointer")
        if isinstance(cand, dict):
            sp_first = cand
    # lossless_text: prefer reconstructed == raw for messaging (engine still experimental).
    out: dict[str, Any] = {
        "ok": True,
        "elapsed_ms": elapsed_ms,
        "compressed_text": comp,
        "reconstructed_text": rec if rec else text,
        "global_ratio": ratio,
        "jaccard": float(jac) if jac is not None else None,
        "semantic_pointer": sp_first,
        "compression_profile": compression_profile,
        "apply_gematria_4d_bridge_policy": _bp,
        "enable_candidate_pool_expansion": pool_on,
    }
    if loss_profile == "lossless_text":
        out["integrity_note"] = "lossless_text_profile_engine_may_still_be_semantic_stub"
    elif loss_profile == "code_equivalent":
        out["integrity_note"] = "code_equivalent_profile_not_isolated_to_nitro_path_in_stub"
    return out


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def _tracka_profile_label() -> str:
    lane = os.environ.get("HYBRID_CODEC_TRACKA_DEFAULT_LANE", "").strip().lower()
    if lane:
        return f"{lane}_default"
    return "c3_domain_gated_default"


def _tracka_profile_source() -> str:
    lane = os.environ.get("HYBRID_CODEC_TRACKA_DEFAULT_LANE", "").strip().lower()
    if lane:
        return "env_tracka_default_lane"
    force_off = os.environ.get("HYBRID_CODEC_PHRASE_FIRST_FORCE_OFF", "").strip().lower()
    if force_off in {"1", "true", "yes", "on"}:
        return "env_force_off"
    raw = os.environ.get("HYBRID_CODEC_PHRASE_FIRST", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return "env_override_on"
    if raw in {"0", "false", "no", "off"}:
        return "env_override_off"
    return "default_promoted"


def _tracka_profile_override_env() -> dict[str, str]:
    """Expose safe, normalized env override state for ops dashboards."""
    raw_force_off = os.environ.get("HYBRID_CODEC_PHRASE_FIRST_FORCE_OFF")
    raw_phrase_first = os.environ.get("HYBRID_CODEC_PHRASE_FIRST")
    force_off_norm = (raw_force_off or "").strip().lower()
    phrase_first_norm = (raw_phrase_first or "").strip().lower()
    return {
        "phrase_first": "set" if raw_phrase_first is not None else "unset",
        "phrase_first_value": phrase_first_norm if phrase_first_norm else "none",
        "force_off": "set" if raw_force_off is not None else "unset",
        "force_off_value": force_off_norm if force_off_norm else "none",
    }


def _tracka_profile_meta() -> dict[str, Any]:
    return {
        "profile": _tracka_profile_label(),
        "source": _tracka_profile_source(),
        "override_env": _tracka_profile_override_env(),
    }


def _tracka_profile_deprecations() -> dict[str, Any]:
    """Transition guide after legacy flat keys were removed from API responses."""
    return {
        "removed_flat_keys": [
            "tracka_profile",
            "tracka_profile_source",
            "tracka_profile_override_env",
        ],
        "replacement": "tracka_profile_meta",
        "status": "legacy_flat_keys_removed",
    }


def _legacy_flat_key_access_count() -> int:
    return int(_LEGACY_FLAT_KEY_ACCESS_COUNT)


def _resolve_atom_id_sequence(
    *,
    text: str | None,
    atom_id_sequence: list[str] | None,
    use_ko_health_sidecar: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    if atom_id_sequence:
        return list(atom_id_sequence), {"status": "ok", "source": "request_body"}
    if not text:
        return [], {"status": "skipped", "reason": "no_text_or_sequence"}
    path = resolve_latest_codebook_path()
    if path is None:
        return [], {"status": "skipped", "reason": "lexicon_missing"}
    if use_ko_health_sidecar:
        from scripts.mkm_inter_agent_ko_health_sidecar_v1 import DEFAULT_SIDECAR, merged_atom_sequence_for_text

        seq, meta = merged_atom_sequence_for_text(text, path, DEFAULT_SIDECAR, tokenization="hangul_syllable")
        flat = {
            "status": "ok",
            "source": "merged_main_and_ko_health_sidecar",
            "hypothesis_tier": "B",
            "research_only": True,
            "ko_health_sidecar": True,
            "atom_id_count": len(seq),
            "merge_meta": meta,
        }
        return seq, flat
    seq, meta = lexicon_atom_sequence_for_text(text, path)
    return seq, meta


def _stub_block_for_packet(
    stub_block: dict[str, Any],
    *,
    stateless_packet: bool,
) -> dict[str, Any]:
    """Trust Packet Stateless Profile: drop full-text leak; keep structured residual fields."""
    if not stateless_packet:
        return stub_block
    return {k: v for k, v in stub_block.items() if k != "reconstructed_text"}


def _expand_codebook_only(pkt: CompressionPacket) -> tuple[str, dict[str, Any]]:
    """Expand without reading mk_stub_v2.reconstructed_text (DoD ② Trust Packet Stateless Profile)."""
    from scripts.report_multilens_performance_eval import _reconstruct_experimental_from_raw

    flags: dict[str, Any] = {"reassembly": "codebook_only"}
    meta = pkt.residual_meta if isinstance(pkt.residual_meta, dict) else {}
    stub = meta.get(RESIDUAL_STUB_KEY) if isinstance(meta.get(RESIDUAL_STUB_KEY), dict) else {}

    if isinstance(stub, dict) and "reconstructed_text" in stub:
        flags["stateless_violation"] = "reconstructed_text_present_in_packet"

    if pkt.loss_profile == "lossless_text":
        hybrid = stub.get("hybrid_codec_v0_payload") if isinstance(stub, dict) else None
        if isinstance(hybrid, dict):
            restored = hybrid_decode_packet_dict(hybrid)
            flags["source"] = "hybrid_codec_v0_payload"
            return restored, flags

    rm = pkt.router_meta if isinstance(pkt.router_meta, dict) else {}
    rm_sid = str(rm.get("shard_id") or "").strip()
    if rm_sid:
        try:
            route = _router.route_from_shard_id(rm_sid)
        except ValueError:
            route = _router.route(pkt.compressed_text)
    else:
        route = _router.route(pkt.compressed_text)
    flags["shard_id"] = route.shard_id
    flags["domain"] = route.domain
    flags["hangul_principle"] = route.hangul_principle

    anchor_text = _reconstruct_experimental_from_raw(
        raw=pkt.compressed_text,
        compressed_candidate=pkt.compressed_text,
        use_hangul_principle=route.hangul_principle,
    )
    text = anchor_text if anchor_text else pkt.compressed_text
    flags["source"] = "compressed_anchor_codebook"

    if isinstance(meta.get("placeholder_map"), dict) and meta.get("placeholder_map"):
        flags["placeholder_map_present"] = True
    if isinstance(meta.get(LEXICON_RAIL_KEY), dict):
        flags["lexicon_rail_present"] = True

    return text, flags


def _attach_lexicon_rail(residual_meta: dict[str, Any], text: str) -> None:
    """Optional 41k atom_id sequence rail (MKM language vocabulary layer)."""
    path = resolve_latest_codebook_path()
    if path is None:
        return
    seq, meta = lexicon_atom_sequence_for_text(text, path)
    if not seq:
        return
    residual_meta[LEXICON_RAIL_KEY] = {
        "symbol_key": "atom_id",
        "atom_id_sequence": seq,
        "lexicon_meta": meta,
    }


def _build_tracka_profile_payload(*, include_legacy_flat_keys: bool) -> dict[str, Any]:
    """Single construction path: meta-first payload."""
    meta = _tracka_profile_meta()
    payload: dict[str, Any] = {
        "tracka_profile_meta": meta,
        "tracka_profile_deprecations": _tracka_profile_deprecations(),
    }
    if include_legacy_flat_keys:
        payload["tracka_profile"] = meta["profile"]
        payload["tracka_profile_source"] = meta["source"]
        payload["tracka_profile_override_env"] = meta["override_env"]
    return payload


def _resolve_hybrid_corpus_binding(body: CompressRequestV2) -> HybridRouterResolution | None:
    tag = str(body.corpus_tag or "").strip()
    if not tag:
        return None
    res = resolve_hybrid_router(tag, sku_class=body.sku_class)
    if res is None:
        if corpus_tag_triggers_shadow(tag, load_shadow_bind_spec()):
            return None
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "error": "unknown_corpus_tag",
                "corpus_tag": tag,
                "hybrid_router_spec": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
            },
        ) from None
    if not res.stub_can_apply_mkm:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "error": "hybrid_router_external_backend",
                "corpus_tag": tag,
                "recommended_backend": res.recommended_backend,
                "message": "v2 stub does not invoke LLMLingua; use scripts/run_compression_hybrid_router_spike_v1.py",
                "research_only": True,
            },
        ) from None
    return res


def _effective_compress_overrides(
    body: CompressRequestV2,
    hybrid_res: HybridRouterResolution | None,
) -> tuple[CompressionProfile, int | None, float | None, set[str]]:
    profile: CompressionProfile = body.compression_profile
    short_thr = body.short_context_token_threshold
    short_max = body.short_context_max_saving_rate
    overlay_extra = {
        str(t).strip()
        for t in (body.must_keep_overlay_terms or [])
        if isinstance(t, str) and str(t).strip()
    }
    if hybrid_res is None:
        return profile, short_thr, short_max, overlay_extra
    if hybrid_res.compression_profile in ("economy", "fidelity", "literal"):
        profile = hybrid_res.compression_profile  # type: ignore[assignment]
    if hybrid_res.short_context_token_threshold is not None:
        short_thr = int(hybrid_res.short_context_token_threshold)
    if hybrid_res.short_context_max_saving_rate is not None:
        short_max = float(hybrid_res.short_context_max_saving_rate)
    if hybrid_res.overlay_terms and not body.must_keep_overlay_terms:
        overlay_extra.update(hybrid_res.overlay_terms)
    return profile, short_thr, short_max, overlay_extra


def _attach_shadow_bind_integrity_flags(
    body: CompressRequestV2,
    route: ShardRoute,
    flags: dict[str, Any],
) -> None:
    tag = str(body.corpus_tag or "").strip()
    if not tag:
        return
    flags.update(
        shadow_bind_integrity_flags(
            text=body.text,
            corpus_tag=tag,
            baseline_route=route,
            router=_router,
        )
    )


@app.get("/health")
def health() -> dict[str, Any]:
    profile_payload = _build_tracka_profile_payload(include_legacy_flat_keys=False)
    return {
        "status": "ok",
        "api_contract_version": API_CONTRACT_VERSION,
        "packet_format_version": PACKET_FORMAT_VERSION,
        "schema_version": "token_compression_stub_v2_draft",
        "stub_engine": "evaluate_report",
        "compression_profiles": ["economy", "fidelity", "literal"],
        "compression_profile_default": "economy",
        "hybrid_codec_router_modes": ["off", "assistant_literal", "economy_fallback"],
        "hybrid_codec_router_default": "off",
        "hybrid_router_spec": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
        "hybrid_router_stub_binding": "partial_stub_metadata",
        "coord_anatomy_wire_stub": "sku_class=coord + anatomy_overlay_coord_v1 → render expand",
        "shadow_bind_stub_metadata": "corpus_tag→integrity_flags only; production route unchanged",
        "shadow_bind_spec": "docs/final/artifacts/compression_en_business_shadow_router_bind_v1.json",
        "anchor_ssot": "reports/constitution/btrack_pilot/comp_4d_anchor_ssot_v1.json",
        "legacy_flat_key_access_count": _legacy_flat_key_access_count(),
        **profile_payload,
    }


def _load_coding_deep_pack_catalog() -> tuple[list[dict[str, Any]], str]:
    import json as _json

    manifest = _json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = load_template_catalog(_TEMPLATES_PATH)
    return rows, str(manifest["catalog_sha256"])


def _coding_deep_pack_lane_active(body: CompressRequestV2, route: ShardRoute) -> bool:
    if body.enable_coding_deep_pack:
        return True
    if body.sku_class == "mask" and route.shard_id == "zone_f_code":
        return True
    return False


def _try_coding_deep_pack_compress(
    body: CompressRequestV2,
    route: ShardRoute,
    flags: dict[str, Any],
) -> CompressResponseV2 | None:
    if not _coding_deep_pack_lane_active(body, route):
        return None
    if not _TEMPLATES_PATH.is_file() or not _MANIFEST_PATH.is_file():
        flags["coding_deep_pack_catalog_missing"] = True
        return None
    rows, catalog_sha256 = _load_coding_deep_pack_catalog()
    resolved = resolve_template_match(body.text, rows)
    if not resolved:
        flags["coding_deep_pack_no_catalog_match"] = True
        return None
    template_id, literal_slots = resolved
    twin = measure_template_wire_twin(
        original_snippet=body.text,
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        catalog_rows=rows,
        literal_slots=literal_slots,
    )
    wire = build_wire_packet(
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        literal_slots=literal_slots,
    )
    stub_block: dict[str, Any] = {
        "reconstructed_text": body.text,
        "global_token_saving_rate": twin["saving_rate"],
        "reconstruction_fidelity_jaccard": twin["jaccard_proxy"],
        "exact_restore_ok": twin["exact_restore_ok"],
    }
    residual_meta: dict[str, Any] = {
        RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=body.stateless_packet),
        "placeholder_map": {},
        CODING_DEEP_PACK_KEY: wire,
    }
    _attach_lexicon_rail(residual_meta, body.text)
    flags.update(
        {
            "coding_deep_pack_wire_v1": True,
            "roundtrip_path": "template_catalog_wire_v1",
            "template_id": template_id,
            "catalog_sha256_short": catalog_sha256[:8],
            "exact_restore_ok": twin["exact_restore_ok"],
            "research_only": True,
        }
    )
    if body.sku_class:
        flags["sku_class"] = body.sku_class
    if literal_slots:
        flags["literal_slots"] = literal_slots
    packet = CompressionPacket(
        loss_profile=body.loss_profile,
        compressed_text=str(twin["wire_compact"]),
        residual_meta=residual_meta,
        router_meta={"shard_id": route.shard_id, "domain": route.domain},
        content_fingerprint=_fingerprint(body.text),
    )
    metrics = CompressionMetricsV2(
        token_in=int(twin["original_token_count"]),
        token_out=int(twin["wire_token_count"]),
        savings_ratio=float(twin["saving_rate"]),
    )
    return CompressResponseV2(
        compression_packet=packet,
        compression_metrics=metrics,
        integrity_flags=flags,
    )


def _load_en_business_deep_pack_catalog() -> tuple[list[dict[str, Any]], str]:
    import json as _json

    manifest = _json.loads(_EB_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = eb_load_template_catalog(_EB_TEMPLATES_PATH)
    return rows, str(manifest["catalog_sha256"])


def _en_business_deep_pack_lane_active(body: CompressRequestV2, route: ShardRoute) -> bool:
    if body.enable_en_business_deep_pack:
        return True
    if body.sku_class == "mask" and route.shard_id == "zone_h_en_business_v1":
        return True
    return False


def _try_en_business_deep_pack_compress(
    body: CompressRequestV2,
    route: ShardRoute,
    flags: dict[str, Any],
) -> CompressResponseV2 | None:
    if not _en_business_deep_pack_lane_active(body, route):
        return None
    if not _EB_TEMPLATES_PATH.is_file() or not _EB_MANIFEST_PATH.is_file():
        flags["en_business_deep_pack_catalog_missing"] = True
        return None
    rows, catalog_sha256 = _load_en_business_deep_pack_catalog()
    resolved = eb_resolve_template_match(body.text, rows)
    if not resolved:
        flags["en_business_deep_pack_no_catalog_match"] = True
        return None
    template_id, _literal_slots = resolved
    twin = eb_measure_template_wire_twin(
        original_snippet=body.text,
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        catalog_rows=rows,
    )
    wire = eb_build_wire_packet(template_id=template_id, catalog_sha256=catalog_sha256)
    stub_block: dict[str, Any] = {
        "reconstructed_text": body.text,
        "global_token_saving_rate": twin["saving_rate"],
        "reconstruction_fidelity_jaccard": twin["jaccard_proxy"],
        "exact_restore_ok": twin["exact_restore_ok"],
    }
    residual_meta: dict[str, Any] = {
        RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=body.stateless_packet),
        "placeholder_map": {},
        EN_BUSINESS_DEEP_PACK_KEY: wire,
    }
    _attach_lexicon_rail(residual_meta, body.text)
    flags.update(
        {
            "en_business_deep_pack_wire_v1": True,
            "roundtrip_path": "template_catalog_wire_v1",
            "wire_family": "BIZ_MASK",
            "template_id": template_id,
            "catalog_sha256_short": catalog_sha256[:8],
            "exact_restore_ok": twin["exact_restore_ok"],
            "research_only": True,
        }
    )
    if body.sku_class:
        flags["sku_class"] = body.sku_class
    packet = CompressionPacket(
        loss_profile=body.loss_profile,
        compressed_text=str(twin["wire_compact"]),
        residual_meta=residual_meta,
        router_meta={"shard_id": route.shard_id, "domain": route.domain},
        content_fingerprint=_fingerprint(body.text),
    )
    metrics = CompressionMetricsV2(
        token_in=int(twin["original_token_count"]),
        token_out=int(twin["wire_token_count"]),
        savings_ratio=float(twin["saving_rate"]),
    )
    return CompressResponseV2(
        compression_packet=packet,
        compression_metrics=metrics,
        integrity_flags=flags,
    )


def _load_ko_premium_cs_deep_pack_catalog() -> tuple[list[dict[str, Any]], str]:
    import json as _json

    manifest = _json.loads(_KCS_MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = kcs_load_template_catalog(_KCS_TEMPLATES_PATH)
    return rows, str(manifest["catalog_sha256"])


def _ko_premium_cs_deep_pack_lane_active(body: CompressRequestV2, route: ShardRoute) -> bool:
    if body.enable_ko_premium_cs_deep_pack:
        return True
    if body.sku_class == "mask" and route.shard_id == "zone_ko_premium_cs_v1":
        return True
    return False


def _try_ko_premium_cs_deep_pack_compress(
    body: CompressRequestV2,
    route: ShardRoute,
    flags: dict[str, Any],
) -> CompressResponseV2 | None:
    if not _ko_premium_cs_deep_pack_lane_active(body, route):
        return None
    if not _KCS_TEMPLATES_PATH.is_file() or not _KCS_MANIFEST_PATH.is_file():
        flags["ko_premium_cs_deep_pack_catalog_missing"] = True
        return None
    rows, catalog_sha256 = _load_ko_premium_cs_deep_pack_catalog()
    resolved = kcs_resolve_template_match(body.text, rows)
    if not resolved:
        flags["ko_premium_cs_deep_pack_no_catalog_match"] = True
        return None
    template_id, _literal_slots = resolved
    twin = kcs_measure_template_wire_twin(
        original_snippet=body.text,
        template_id=template_id,
        catalog_sha256=catalog_sha256,
        catalog_rows=rows,
    )
    wire = kcs_build_wire_packet(template_id=template_id, catalog_sha256=catalog_sha256)
    stub_block: dict[str, Any] = {
        "reconstructed_text": body.text,
        "global_token_saving_rate": twin["saving_rate"],
        "reconstruction_fidelity_jaccard": twin["jaccard_proxy"],
        "exact_restore_ok": twin["exact_restore_ok"],
    }
    residual_meta: dict[str, Any] = {
        RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=body.stateless_packet),
        "placeholder_map": {},
        KO_PREMIUM_CS_DEEP_PACK_KEY: wire,
    }
    _attach_lexicon_rail(residual_meta, body.text)
    flags.update(
        {
            "ko_premium_cs_deep_pack_wire_v1": True,
            "roundtrip_path": "template_catalog_wire_v1",
            "wire_family": "CS_MASK",
            "template_id": template_id,
            "catalog_sha256_short": catalog_sha256[:8],
            "exact_restore_ok": twin["exact_restore_ok"],
            "research_only": True,
        }
    )
    if body.sku_class:
        flags["sku_class"] = body.sku_class
    packet = CompressionPacket(
        loss_profile=body.loss_profile,
        compressed_text=str(twin["wire_compact"]),
        residual_meta=residual_meta,
        router_meta={"shard_id": route.shard_id, "domain": route.domain},
        content_fingerprint=_fingerprint(body.text),
    )
    metrics = CompressionMetricsV2(
        token_in=int(twin["original_token_count"]),
        token_out=int(twin["wire_token_count"]),
        savings_ratio=float(twin["saving_rate"]),
    )
    return CompressResponseV2(
        compression_packet=packet,
        compression_metrics=metrics,
        integrity_flags=flags,
    )


def _coord_anatomy_lane_active(body: CompressRequestV2) -> bool:
    if body.sku_class == "coord":
        return True
    wire = parse_coord_wire_text(body.text)
    return wire is not None and wire.get("wire_mode") == COORD_ANATOMY_WIRE_MODE


def _try_coord_anatomy_compress(
    body: CompressRequestV2,
    route: ShardRoute,
    flags: dict[str, Any],
) -> CompressResponseV2 | None:
    if not _coord_anatomy_lane_active(body):
        return None
    wire = parse_coord_wire_text(body.text)
    if not wire or wire.get("wire_mode") != COORD_ANATOMY_WIRE_MODE:
        flags["coord_anatomy_wire_reject"] = True
        return None
    compact = compact_coord_wire(wire)
    tin = _token_count_proxy(body.text)
    tout = _token_count_proxy(compact)
    sr = max(0.0, min(1.0, 1.0 - (float(tout or 0) / float(max(1, tin or 1)))))
    stub_block: dict[str, Any] = {
        "reconstructed_text": body.text,
        "global_token_saving_rate": sr,
        "reconstruction_fidelity_jaccard": 1.0,
        "exact_restore_ok": True,
    }
    residual_meta: dict[str, Any] = {
        RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=body.stateless_packet),
        "placeholder_map": {},
        COORD_WIRE_KEY: wire,
    }
    flags.update(
        {
            "coord_anatomy_overlay_wire_v1": True,
            "sku_class": "coord",
            "wire_mode": COORD_ANATOMY_WIRE_MODE,
            "roundtrip_path": "coord_anatomy_render_v1",
            "research_only": True,
        }
    )
    packet = CompressionPacket(
        loss_profile=body.loss_profile,
        compressed_text=compact,
        residual_meta=residual_meta,
        router_meta={"shard_id": route.shard_id, "domain": route.domain},
        content_fingerprint=_fingerprint(body.text),
    )
    metrics = CompressionMetricsV2(token_in=tin, token_out=tout, savings_ratio=sr)
    return CompressResponseV2(
        compression_packet=packet,
        compression_metrics=metrics,
        integrity_flags=flags,
    )


def _try_expand_coord_anatomy(pkt: CompressionPacket) -> tuple[str, dict[str, Any]] | None:
    meta = pkt.residual_meta if isinstance(pkt.residual_meta, dict) else {}
    wire = meta.get(COORD_WIRE_KEY) if isinstance(meta, dict) else None
    if not isinstance(wire, dict):
        parsed = parse_coord_wire_text(str(pkt.compressed_text or ""))
        if isinstance(parsed, dict) and not parsed.get("_compact_only"):
            wire = parsed
    if not isinstance(wire, dict) or wire.get("wire_mode") != COORD_ANATOMY_WIRE_MODE:
        return None
    try:
        return expand_coord_wire_to_text(wire, workspace_root=ROOT)
    except (FileNotFoundError, ValueError, OSError) as exc:
        err = json.dumps(
            {"schema": "coord_anatomy_overlay_expand_v1", "ok": False, "error": str(exc)},
            ensure_ascii=False,
        )
        return err, {
            "reassembly": "coord_anatomy_overlay_wire_v1",
            "coord_render_failed": True,
            "research_only": True,
        }


def _try_expand_coding_deep_pack(pkt: CompressionPacket) -> tuple[str, dict[str, Any]] | None:
    compact = str(pkt.compressed_text or "")
    meta = pkt.residual_meta if isinstance(pkt.residual_meta, dict) else {}
    wire_info = meta.get(CODING_DEEP_PACK_KEY) if isinstance(meta, dict) else None
    if not compact.startswith("[ZF_MASK:") and not isinstance(wire_info, dict):
        return None
    if not _TEMPLATES_PATH.is_file() or not _MANIFEST_PATH.is_file():
        return None
    rows, catalog_sha256 = _load_coding_deep_pack_catalog()
    try:
        if compact.startswith("[ZF_MASK:"):
            text = expand_template_wire(compact, rows, expected_catalog_sha256=catalog_sha256)
        elif isinstance(wire_info, dict):
            text = expand_template_wire(wire_info, rows, expected_catalog_sha256=catalog_sha256)
        else:
            return None
    except (KeyError, ValueError):
        return None
    return text, {
        "reassembly": "coding_deep_pack_wire_v1",
        "source": CODING_DEEP_PACK_KEY,
        "exact_restore_ok": True,
        "roundtrip_path": "template_catalog_wire_v1",
        "research_only": True,
    }


def _try_expand_en_business_deep_pack(pkt: CompressionPacket) -> tuple[str, dict[str, Any]] | None:
    compact = str(pkt.compressed_text or "")
    meta = pkt.residual_meta if isinstance(pkt.residual_meta, dict) else {}
    wire_info = meta.get(EN_BUSINESS_DEEP_PACK_KEY) if isinstance(meta, dict) else None
    if not compact.startswith("[BIZ_MASK:") and not isinstance(wire_info, dict):
        return None
    if not _EB_TEMPLATES_PATH.is_file() or not _EB_MANIFEST_PATH.is_file():
        return None
    rows, catalog_sha256 = _load_en_business_deep_pack_catalog()
    try:
        if compact.startswith("[BIZ_MASK:"):
            text = eb_expand_template_wire(compact, rows, expected_catalog_sha256=catalog_sha256)
        elif isinstance(wire_info, dict):
            text = eb_expand_template_wire(wire_info, rows, expected_catalog_sha256=catalog_sha256)
        else:
            return None
    except (KeyError, ValueError):
        return None
    return text, {
        "reassembly": "en_business_deep_pack_wire_v1",
        "source": EN_BUSINESS_DEEP_PACK_KEY,
        "exact_restore_ok": True,
        "roundtrip_path": "template_catalog_wire_v1",
        "wire_family": "BIZ_MASK",
        "research_only": True,
    }


def _try_expand_ko_premium_cs_deep_pack(pkt: CompressionPacket) -> tuple[str, dict[str, Any]] | None:
    compact = str(pkt.compressed_text or "")
    meta = pkt.residual_meta if isinstance(pkt.residual_meta, dict) else {}
    wire_info = meta.get(KO_PREMIUM_CS_DEEP_PACK_KEY) if isinstance(meta, dict) else None
    if not compact.startswith("[CS_MASK:") and not isinstance(wire_info, dict):
        return None
    if not _KCS_TEMPLATES_PATH.is_file() or not _KCS_MANIFEST_PATH.is_file():
        return None
    rows, catalog_sha256 = _load_ko_premium_cs_deep_pack_catalog()
    try:
        if compact.startswith("[CS_MASK:"):
            text = kcs_expand_template_wire(compact, rows, expected_catalog_sha256=catalog_sha256)
        elif isinstance(wire_info, dict):
            text = kcs_expand_template_wire(wire_info, rows, expected_catalog_sha256=catalog_sha256)
        else:
            return None
    except (KeyError, ValueError):
        return None
    return text, {
        "reassembly": "ko_premium_cs_deep_pack_wire_v1",
        "source": KO_PREMIUM_CS_DEEP_PACK_KEY,
        "exact_restore_ok": True,
        "roundtrip_path": "template_catalog_wire_v1",
        "wire_family": "CS_MASK",
        "research_only": True,
    }


@app.post("/v2/compress", response_model=CompressResponseV2)
def compress_v2(body: CompressRequestV2) -> CompressResponseV2:
    forced_sid = str(body.forced_shard_id or "").strip() or None
    hybrid_res = _resolve_hybrid_corpus_binding(body)
    requested_profile, short_thr_override, short_max_override, overlay_extra = _effective_compress_overrides(
        body, hybrid_res
    )
    try:
        route = _resolve_router_route(body.text, forced_sid)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=str(exc)) from exc
    flags: dict[str, Any] = {
        "stub_v2": True,
        "hangul_principle": route.hangul_principle,
        "loss_profile": body.loss_profile,
        **profile_meta(requested_profile),
        **_build_tracka_profile_payload(include_legacy_flat_keys=False),
    }
    if hybrid_res is not None:
        flags.update(corpus_binding_integrity_flags(hybrid_res))
    _attach_shadow_bind_integrity_flags(body, route, flags)
    if forced_sid:
        flags["forced_shard_id"] = forced_sid
        flags["forced_shard_promoted_b2b"] = forced_sid.endswith("_b2b_v1")
    if body.stateless_packet:
        flags["stateless_packet"] = True
    coord_resp = _try_coord_anatomy_compress(body, route, flags)
    if coord_resp is not None:
        return coord_resp
    coding_resp = _try_coding_deep_pack_compress(body, route, flags)
    if coding_resp is not None:
        return coding_resp
    if flags.get("coding_deep_pack_no_catalog_match"):
        flags["coding_deep_pack_fallback_path"] = "semantic_v2_stub"
    en_resp = _try_en_business_deep_pack_compress(body, route, flags)
    if en_resp is not None:
        return en_resp
    if flags.get("en_business_deep_pack_no_catalog_match"):
        flags["en_business_deep_pack_fallback_path"] = "semantic_v2_stub"
    kcs_resp = _try_ko_premium_cs_deep_pack_compress(body, route, flags)
    if kcs_resp is not None:
        return kcs_resp
    if flags.get("ko_premium_cs_deep_pack_no_catalog_match"):
        flags["ko_premium_cs_deep_pack_fallback_path"] = "semantic_v2_stub"
    try:
        # Fused lane: lossless_text goes through deterministic hybrid codec first.
        if body.loss_profile == "lossless_text":
            hybrid_payload = hybrid_encode_packet_dict(body.text)
            restored = hybrid_decode_packet_dict(hybrid_payload)
            encoded = " ".join([str(x) for x in (hybrid_payload.get("body_tokens") or [])])
            in_len = max(1, int(hybrid_payload.get("input_char_len") or 0))
            out_len = int(hybrid_payload.get("output_char_len") or 0)
            savings = max(0.0, min(1.0, 1.0 - (float(out_len) / float(in_len))))
            flags["hybrid_codec_v0_fused"] = True
            flags["hybrid_codec_v0_exact_restore_ok"] = restored == body.text
            hybrid_stub: dict[str, Any] = {
                "reconstructed_text": restored,
                "global_token_saving_rate": savings,
                "reconstruction_fidelity_jaccard": _jaccard(body.text, restored),
                "hybrid_codec_v0_payload": hybrid_payload,
            }
            residual_meta = {
                RESIDUAL_STUB_KEY: _stub_block_for_packet(hybrid_stub, stateless_packet=body.stateless_packet),
                "placeholder_map": {},
            }
            _attach_lexicon_rail(residual_meta, body.text)
            packet = CompressionPacket(
                loss_profile=body.loss_profile,
                compressed_text=encoded,
                residual_meta=residual_meta,
                router_meta={"shard_id": route.shard_id, "domain": route.domain},
                content_fingerprint=_fingerprint(body.text),
            )
            tin = _token_count_proxy(body.text)
            tout = _token_count_proxy(encoded)
            metrics = CompressionMetricsV2(token_in=tin, token_out=tout, savings_ratio=savings)
            return CompressResponseV2(
                compression_packet=packet,
                compression_metrics=metrics,
                integrity_flags=flags,
            )

        plan = resolve_hybrid_codec_plan(
            router=body.hybrid_codec_router,
            session_turns=body.session_turns,
            requested_profile=requested_profile,
            short_context_token_threshold=short_thr_override,
            short_context_max_saving_rate=short_max_override,
        )
        shortcap = plan.get("economy_shortcap") or {}
        effective_profile: CompressionProfile = plan["effective_profile"]  # type: ignore[assignment]
        effective_routing: RoutingProfile = body.routing_profile
        enable_pool = bool(body.enable_candidate_pool_expansion)
        if hybrid_res is not None:
            rp = hybrid_res.routing_profile
            if rp in ("default", "track_a_promoted", "b_track_domain_relax", "candidate_pool_on"):
                effective_routing = rp  # type: ignore[assignment]
            if hybrid_res.enable_candidate_pool_expansion:
                enable_pool = True
        ev = _run_evaluate_for_packet(
            body.text,
            body.loss_profile,
            emit_semantic_pointer=bool(body.emit_semantic_pointer),
            graph_wire_selective_bridge=bool(body.graph_wire_selective_bridge),
            client_request_id=body.client_request_id,
            routing_profile=effective_routing,
            compression_profile=effective_profile,
            force_shard_id=forced_sid,
            extra_must_keep=overlay_extra if overlay_extra else None,
            short_context_token_threshold=shortcap.get("short_context_token_threshold")
            if shortcap.get("short_context_token_threshold") is not None
            else short_thr_override,
            short_context_max_saving_rate=shortcap.get("short_context_max_saving_rate")
            if shortcap.get("short_context_max_saving_rate") is not None
            else short_max_override,
            short_context_disable_min_saving_floor=body.short_context_disable_min_saving_floor,
            enable_candidate_pool_expansion=enable_pool,
        )
        gr = ev.get("global_ratio")
        gr_typed: float | None = float(gr) if gr is not None else None
        rec_raw = str(ev.get("reconstructed_text") or body.text)
        comp_raw = str(ev.get("compressed_text") or body.text)
        comp, rec, ratio_final, jac_after, trust_restored = _apply_v2_trust_restoration(
            body.text, comp_raw, rec_raw, gr_typed
        )
        gate_jac = _hybrid_fallback_gate_jaccard(
            body.text,
            ev,
            loss_profile=body.loss_profile,
            route=route,
            stateless_packet=body.stateless_packet,
            jac_after_trust=jac_after,
        )
        if (
            body.hybrid_codec_router == "economy_fallback"
            and gate_jac < HYBRID_CODEC_JACCARD_FLOOR
        ):
            plan["economy_attempt"] = {
                "ok": False,
                "jaccard_proxy": round(float(gate_jac), 6),
                "compression_profile": "economy",
                "gate": "stateless_codebook_only" if body.stateless_packet else "trust_restored",
            }
            ev = _run_evaluate_for_packet(
                body.text,
                body.loss_profile,
                emit_semantic_pointer=bool(body.emit_semantic_pointer),
                graph_wire_selective_bridge=bool(body.graph_wire_selective_bridge),
                client_request_id=body.client_request_id,
                routing_profile=effective_routing,
                compression_profile="literal",
                force_shard_id=forced_sid,
                extra_must_keep=overlay_extra if overlay_extra else None,
                short_context_token_threshold=None,
                short_context_max_saving_rate=None,
                short_context_disable_min_saving_floor=body.short_context_disable_min_saving_floor,
                enable_candidate_pool_expansion=enable_pool,
            )
            gr = ev.get("global_ratio")
            gr_typed = float(gr) if gr is not None else None
            rec_raw = str(ev.get("reconstructed_text") or body.text)
            comp_raw = str(ev.get("compressed_text") or body.text)
            comp, rec, ratio_final, jac_after, trust_restored = _apply_v2_trust_restoration(
                body.text, comp_raw, rec_raw, gr_typed
            )
            plan["fallback_used"] = True
            plan["profiles_tried"] = ["economy", "literal"]
            plan["route_reason"] = "literal_fallback_after_economy_fail"
            plan["effective_profile"] = "literal"
            effective_profile = "literal"
        if body.must_keep_overlay_terms:
            flags["must_keep_overlay_terms_count"] = len(body.must_keep_overlay_terms)
        short_thr = shortcap.get("short_context_token_threshold")
        if short_thr is not None:
            flags["short_context_token_threshold"] = short_thr
            flags["short_context_max_saving_rate"] = shortcap.get("short_context_max_saving_rate")
            flags["short_context_policy_applied"] = _token_count_proxy(body.text) <= int(short_thr)
        flags["evaluate_report_ms"] = ev.get("elapsed_ms")
        flags["routing_profile"] = effective_routing
        if enable_pool:
            flags["enable_candidate_pool_expansion"] = True
        flags.update(profile_meta(effective_profile))
        flags.update(hybrid_router_integrity_flags(plan))
        flags["compression_profile_requested"] = requested_profile
        flags["compression_profile_effective"] = effective_profile
        if body.hybrid_codec_router != "off":
            flags["hybrid_codec_gate_jaccard"] = round(float(gate_jac), 6)
        flags["apply_gematria_4d_bridge_policy_effective"] = bool(
            ev.get("apply_gematria_4d_bridge_policy")
        )
        flags["v2_case_id"] = resolve_v2_case_id(body.client_request_id)
        route_meta = routing_profile_kwargs(body.routing_profile)
        if route_meta.get("research_only"):
            flags["routing_research_only"] = True
        if route_meta.get("promotion_signoff_path"):
            flags["promotion_signoff_path"] = route_meta["promotion_signoff_path"]
        if route_meta.get("candidate_artifact_path"):
            flags["candidate_pool_artifact_path"] = route_meta["candidate_artifact_path"]
        if ev.get("enable_candidate_pool_expansion") or body.enable_candidate_pool_expansion:
            flags["enable_candidate_pool_expansion"] = True
        if not ev.get("ok"):
            flags["evaluate_report_degraded"] = True
        flags["jaccard_proxy"] = jac_after
        if trust_restored:
            flags["jaccard_trust_restoration"] = True
            flags["jaccard_pre_restoration"] = ev.get("jaccard")
        if ev.get("integrity_note"):
            flags["integrity_note"] = ev.get("integrity_note")
        stub_block: dict[str, Any] = {
            "reconstructed_text": rec,
            "global_token_saving_rate": ratio_final,
            "reconstruction_fidelity_jaccard": jac_after,
        }
        sp_ev = ev.get("semantic_pointer")
        if isinstance(sp_ev, dict):
            stub_block["semantic_pointer"] = sp_ev
            gw = sp_ev.get("graph_wire_influence_v1")
            if isinstance(gw, dict):
                flags["graph_wire_influence_v1"] = True
                flags["graph_wire_bridge_boost"] = bool(gw.get("bridge_boost"))
        residual_meta = {
            RESIDUAL_STUB_KEY: _stub_block_for_packet(stub_block, stateless_packet=body.stateless_packet),
            "placeholder_map": {},
        }
        _attach_lexicon_rail(residual_meta, body.text)
        packet = CompressionPacket(
            loss_profile=body.loss_profile,
            compressed_text=comp,
            residual_meta=residual_meta,
            router_meta={"shard_id": route.shard_id, "domain": route.domain},
            content_fingerprint=_fingerprint(body.text),
        )
        tin = _token_count_proxy(body.text)
        tout = _token_count_proxy(comp)
        if ratio_final is None:
            sr = None
        else:
            sr = max(0.0, min(1.0, float(ratio_final)))
        metrics = CompressionMetricsV2(token_in=tin, token_out=tout, savings_ratio=sr)
        return CompressResponseV2(
            compression_packet=packet,
            compression_metrics=metrics,
            integrity_flags=flags,
        )
    except Exception as exc:
        flags["evaluate_report_failed"] = True
        flags["error_class"] = type(exc).__name__
        err_stub = _stub_block_for_packet(
            {
                "reconstructed_text": body.text,
                "error_class": type(exc).__name__,
            },
            stateless_packet=body.stateless_packet,
        )
        residual_meta = {
            RESIDUAL_STUB_KEY: err_stub,
            "placeholder_map": {},
        }
        packet = CompressionPacket(
            loss_profile=body.loss_profile,
            compressed_text=body.text,
            residual_meta=residual_meta,
            router_meta={"shard_id": route.shard_id, "domain": route.domain},
            content_fingerprint=_fingerprint(body.text),
        )
        return CompressResponseV2(
            compression_packet=packet,
            compression_metrics=None,
            integrity_flags=flags,
        )


@app.post("/v2/expand", response_model=ExpandResponseV2)
def expand_v2(body: ExpandRequestV2) -> ExpandResponseV2:
    pkt = body.compression_packet
    mode = body.decode_mode
    flags: dict[str, Any] = {"stub_v2": True, "decode_mode": mode}

    coord = _try_expand_coord_anatomy(pkt)
    if coord is not None:
        text, extra = coord
        flags.update(extra)
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)

    coding = _try_expand_coding_deep_pack(pkt)
    if coding is not None:
        text, extra = coding
        flags.update(extra)
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)

    en_biz = _try_expand_en_business_deep_pack(pkt)
    if en_biz is not None:
        text, extra = en_biz
        flags.update(extra)
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)

    kcs = _try_expand_ko_premium_cs_deep_pack(pkt)
    if kcs is not None:
        text, extra = kcs
        flags.update(extra)
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)

    if mode == "codebook_only":
        text, cb_flags = _expand_codebook_only(pkt)
        flags.update(cb_flags)
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)

    if mode == "l1_experimental":
        from scripts.mkm_inter_agent_l1_decode_experimental_v1 import (  # noqa: WPS433
            decode_compressed_observation_experimental,
        )

        l1 = decode_compressed_observation_experimental(pkt.compressed_text, beam_size=4)
        flags["research_only"] = True
        flags["reassembly"] = "l1_experimental_beam"
        flags["l1_decode"] = {k: v for k, v in l1.items() if k != "decoded_text"}
        if not l1.get("ok"):
            flags["l1_decode_failed"] = True
            text = pkt.compressed_text
            flags["reassembly"] = "l1_experimental_degraded_compressed_text"
        else:
            text = str(l1.get("decoded_text") or pkt.compressed_text)
        return ExpandResponseV2(
            text=text,
            decode_mode=mode,
            integrity_flags=flags,
        )

    flags["reassembly"] = "residual_meta"
    meta = pkt.residual_meta or {}
    stub = meta.get(RESIDUAL_STUB_KEY) if isinstance(meta, dict) else None
    if isinstance(stub, dict) and "reconstructed_text" in stub:
        text = str(stub["reconstructed_text"])
        flags["source"] = RESIDUAL_STUB_KEY
        return ExpandResponseV2(text=text, decode_mode=mode, integrity_flags=flags)
    flags["reassembly"] = "degraded_compressed_text_only"
    return ExpandResponseV2(text=pkt.compressed_text, decode_mode=mode, integrity_flags=flags)


def _lexicon_wire_payload(atom_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": LEXICON_WIRE_SCHEMA,
        "atom_id_sequence": atom_ids,
        "atom_count": len(atom_ids),
    }


@app.post("/v1/research/mkm_lexicon_wire/encode", response_model=MkmLexiconWireEncodeResponse)
def encode_mkm_lexicon_wire(body: MkmLexiconWireEncodeRequest) -> MkmLexiconWireEncodeResponse:
    """Research lane: atom_id_sequence only on adaptive msgpack wire (no Trust Packet JSON)."""
    from scripts.l1_side_channel_wire_codec import decode_adaptive_msgpack, encode_adaptive_msgpack  # noqa: WPS433

    atom_ids, lex_meta = _resolve_atom_id_sequence(
        text=body.text,
        atom_id_sequence=body.atom_id_sequence,
        use_ko_health_sidecar=body.use_ko_health_sidecar,
    )
    if not atom_ids:
        return MkmLexiconWireEncodeResponse(
            wire_b64="",
            wire_byte_len=0,
            codec_variant="none",
            atom_id_sequence=[],
            lexicon_meta=lex_meta,
            integrity_flags={
                "research_only": True,
                "error": "empty_atom_id_sequence",
            },
        )
    payload = _lexicon_wire_payload(atom_ids)
    try:
        wire_bytes, variant = encode_adaptive_msgpack(
            payload,
            zstd_min_raw_bytes=body.zstd_min_raw_bytes,
            zstd_level=body.zstd_level,
        )
        decoded = decode_adaptive_msgpack(wire_bytes)
        assert decoded.get("atom_id_sequence") == atom_ids
    except Exception as exc:
        return MkmLexiconWireEncodeResponse(
            wire_b64="",
            wire_byte_len=0,
            codec_variant="none",
            atom_id_sequence=atom_ids,
            lexicon_meta=lex_meta,
            integrity_flags={
                "research_only": True,
                "error": "wire_encode_failed",
                "error_class": type(exc).__name__,
            },
        )
    codec_variant = "zstd_msgpack" if variant == "zstd" else "raw_msgpack"
    return MkmLexiconWireEncodeResponse(
        wire_b64=base64.b64encode(wire_bytes).decode("ascii"),
        wire_byte_len=len(wire_bytes),
        codec_variant=codec_variant,
        atom_id_sequence=atom_ids,
        lexicon_meta=lex_meta,
        integrity_flags={
            "research_only": True,
            "roundtrip_sanity": True,
            **(
                {"ko_health_sidecar": True, "hypothesis_tier": "B"}
                if body.use_ko_health_sidecar
                else {}
            ),
        },
    )


@app.post("/v1/research/mkm_lexicon_wire/decode", response_model=MkmLexiconWireDecodeResponse)
def decode_mkm_lexicon_wire(body: MkmLexiconWireDecodeRequest) -> MkmLexiconWireDecodeResponse:
    """Research lane: decode lexicon wire blob back to atom_id_sequence."""
    from scripts.l1_side_channel_wire_codec import decode_adaptive_msgpack  # noqa: WPS433

    try:
        wire_bytes = base64.b64decode(body.wire_b64.encode("ascii"))
        payload = decode_adaptive_msgpack(wire_bytes)
    except Exception as exc:
        return MkmLexiconWireDecodeResponse(
            payload={},
            atom_id_sequence=[],
            integrity_flags={
                "research_only": True,
                "error": "wire_decode_failed",
                "error_class": type(exc).__name__,
            },
        )
    atom_ids = payload.get("atom_id_sequence") if isinstance(payload, dict) else []
    if not isinstance(atom_ids, list):
        atom_ids = []
    return MkmLexiconWireDecodeResponse(
        payload=payload if isinstance(payload, dict) else {},
        atom_id_sequence=[str(x) for x in atom_ids],
        integrity_flags={"research_only": True},
    )


@app.post("/v1/research/mkm_inter_agent_wire/turn", response_model=MkmWireTurnResponse)
def send_mkm_wire_turn_v1(body: MkmWireTurnRequest) -> MkmWireTurnResponse:
    """Research lane: one turn -> wire envelope v1 (M6/M7 runtime adapter path)."""
    from scripts.mkm_inter_agent_wire_envelope_v1 import (
        build_turn_envelope,
        envelope_utf8_byte_len,
        new_session_id,
    )

    enc_req = MkmLexiconWireEncodeRequest(
        text=body.text,
        zstd_min_raw_bytes=body.zstd_min_raw_bytes,
        use_ko_health_sidecar=body.use_ko_health_sidecar,
    )
    enc_resp = encode_mkm_lexicon_wire(enc_req)
    if not enc_resp.wire_b64:
        return MkmWireTurnResponse(
            envelope={},
            envelope_utf8_byte_len=0,
            integrity_flags={"research_only": True, "error": "encode_failed"},
        )
    sid = body.session_id or new_session_id("api")
    envelope = build_turn_envelope(
        encode_response={
            "wire_b64": enc_resp.wire_b64,
            "wire_byte_len": enc_resp.wire_byte_len,
            "codec_variant": enc_resp.codec_variant,
            "atom_id_sequence": enc_resp.atom_id_sequence,
            "lexicon_meta": enc_resp.lexicon_meta,
        },
        session_id=sid,
        turn_id=body.turn_id,
        from_agent=body.from_agent,
        to_agent=body.to_agent,
        loss_profile=body.loss_profile,
        routing_profile=body.routing_profile,
    )
    env_len = envelope_utf8_byte_len(envelope)
    return MkmWireTurnResponse(
        envelope=envelope,
        envelope_utf8_byte_len=env_len,
        integrity_flags={"research_only": True, "runtime_adapter": "mkm_inter_agent_wire_runtime_adapter_v1"},
    )


@app.post("/v1/research/mkm_inter_agent_wire/replay", response_model=MkmWireReplayResponse)
def replay_mkm_wire_session_v1(body: MkmWireReplayRequest) -> MkmWireReplayResponse:
    """Research lane: replay wire envelopes → gloss (+ optional wire decode check)."""
    from scripts.mkm_inter_agent_wire_replay_v1 import replay_envelopes, replay_scenario_demo

    if body.envelopes:
        result = replay_envelopes(body.envelopes)
    elif body.scenario in ("trading", "health", "lexicon_dense"):
        result = replay_scenario_demo(
            scenario=body.scenario,
            turns=body.turns,
            use_ko_health_sidecar=body.use_ko_health_sidecar,
        )
    else:
        return MkmWireReplayResponse(
            turn_count=0,
            turns=[],
            integrity_flags={"research_only": True, "error": "envelopes_or_scenario_required"},
        )
    return MkmWireReplayResponse(
        turn_count=int(result.get("turn_count") or 0),
        turns=result.get("turns") or [],
        scenario=result.get("scenario"),
        session_id=result.get("session_id"),
        integrity_flags={
            "research_only": True,
            "ok": bool(result.get("ok")),
            **(result.get("integrity_flags") or {}),
        },
    )
