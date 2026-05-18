#!/usr/bin/env python3
"""FastAPI v2 draft: Trust Packet round-trip (openapi_token_compression_v2_draft.yaml, Fact-Lock §11).

Run: uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011

Compress uses ``evaluate_report`` (same family as v1 live hydration). The packet's ``residual_meta``
includes ``mk_stub_v2.reconstructed_text`` so ``POST /v2/expand`` can return engine reconstruction
without echoing a separate v1 ``original_text`` field — still experimental, not a production SLA.
``GlobalPivotCompressionPipeline`` is not used; name in early drafts was superseded by this path.

Dev: MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY=1 enables full gematria/4D bridge policy in evaluate_report (see compression_token_api_stub).
"""

from __future__ import annotations

import hashlib
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

from scripts.compression_token_api_stub import (  # noqa: E402
    TOKEN_RE,
    _baseline_avg_jaccard,
    _decision_selected_profile,
)
from scripts.core.domain_router import DomainSpecificRouter  # noqa: E402
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
# Same multiset definition as tests (`_jaccard`); floor aligns with Track A round-trip targets.
V2_JACCARD_TRUST_MIN = 0.73
_LEGACY_FLAT_KEY_ACCESS_COUNT = 0

SHARDS = ROOT / "codebook" / "shards"
_router = DomainSpecificRouter(SHARDS)

LossProfile = Literal["lossless_text", "semantic_general", "code_equivalent"]

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
    locale: str | None = None
    client_request_id: str | None = None
    notes: str | None = None
    emit_semantic_pointer: bool = False


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


DecodeMode = Literal["stub", "l1_experimental"]


class ExpandRequestV2(BaseModel):
    compression_packet: CompressionPacket
    decode_mode: DecodeMode = "stub"


class ExpandResponseV2(BaseModel):
    text: str
    api_contract_version: str = API_CONTRACT_VERSION
    decode_mode: DecodeMode = "stub"
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


def _run_evaluate_for_packet(
    text: str, loss_profile: LossProfile, *, emit_semantic_pointer: bool = False
) -> dict[str, Any]:
    """Run evaluate_report and return payload for Trust Packet fields."""
    selected = _decision_selected_profile()
    strategy = str(selected.get("strategy", "A"))
    intensity = str(selected.get("intensity", "extreme"))
    general_cap = selected.get("general_max_saving_rate")
    sensitive_cap = selected.get("sensitive_max_saving_rate")
    hangul_cap = selected.get("hangul_max_saving_rate")
    t0 = perf_counter()
    doc = {
        "compression_cases": [
            {
                "id": "v2-trust-packet",
                "raw_text": text,
                "compressed_text": "",
                "reconstructed_text": "",
            }
        ],
        "fusion_answer_cases": [],
    }
    _bp = env_apply_gematria_4d_bridge_policy()
    report = evaluate_report(
        doc,
        source_input="api:v2_trust_packet",
        mode="experimental",
        strategy=strategy if strategy in {"A", "B", "C"} else "A",
        intensity=intensity if intensity in {"high", "ultra", "extreme"} else "extreme",
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=1.5,
        baseline_avg_jaccard=_baseline_avg_jaccard(),
        general_max_saving_rate=float(general_cap) if general_cap is not None else None,
        sensitive_max_saving_rate=float(sensitive_cap) if sensitive_cap is not None else None,
        hangul_max_saving_rate=float(hangul_cap) if hangul_cap is not None else None,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=_bp,
        include_gematria_4d_bridge=_bp,
        include_cee_core=_bp,
        apply_gematria_4d_bridge_policy=_bp,
        emit_semantic_pointer=emit_semantic_pointer,
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


@app.get("/health")
def health() -> dict[str, Any]:
    profile_payload = _build_tracka_profile_payload(include_legacy_flat_keys=False)
    return {
        "status": "ok",
        "api_contract_version": API_CONTRACT_VERSION,
        "packet_format_version": PACKET_FORMAT_VERSION,
        "schema_version": "token_compression_stub_v2_draft",
        "stub_engine": "evaluate_report",
        "legacy_flat_key_access_count": _legacy_flat_key_access_count(),
        **profile_payload,
    }


@app.post("/v2/compress", response_model=CompressResponseV2)
def compress_v2(body: CompressRequestV2) -> CompressResponseV2:
    route = _router.route(body.text)
    flags: dict[str, Any] = {
        "stub_v2": True,
        "hangul_principle": route.hangul_principle,
        "loss_profile": body.loss_profile,
        **_build_tracka_profile_payload(include_legacy_flat_keys=False),
    }
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
            residual_meta = {
                RESIDUAL_STUB_KEY: {
                    "reconstructed_text": restored,
                    "global_token_saving_rate": savings,
                    "reconstruction_fidelity_jaccard": _jaccard(body.text, restored),
                    "hybrid_codec_v0_payload": hybrid_payload,
                },
                "placeholder_map": {},
            }
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

        ev = _run_evaluate_for_packet(
            body.text, body.loss_profile, emit_semantic_pointer=bool(body.emit_semantic_pointer)
        )
        flags["evaluate_report_ms"] = ev.get("elapsed_ms")
        if not ev.get("ok"):
            flags["evaluate_report_degraded"] = True
        gr = ev.get("global_ratio")
        gr_typed: float | None = float(gr) if gr is not None else None
        rec_raw = str(ev.get("reconstructed_text") or body.text)
        comp_raw = str(ev.get("compressed_text") or body.text)
        comp, rec, ratio_final, jac_after, trust_restored = _apply_v2_trust_restoration(
            body.text, comp_raw, rec_raw, gr_typed
        )
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
        residual_meta = {
            RESIDUAL_STUB_KEY: stub_block,
            "placeholder_map": {},
        }
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
        residual_meta = {
            RESIDUAL_STUB_KEY: {
                "reconstructed_text": body.text,
                "error_class": type(exc).__name__,
            },
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
