#!/usr/bin/env python3
"""FastAPI stub: domain router + optional hydration (FACT-LOCK: openapi_token_compression_stub_v1.yaml, COMPRESSION_* §10).

Run: uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010

When eval_context.hydrate_metrics and hydrate_live_eval are true, calls evaluate_report; on exception sets
integrity_flags hydration_live_eval_failed and may fall back to decision-based estimates.

Dev: set MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY=1 to enable gematria metadata + 4D bridge + CEE + bridge policy in live evaluate_report (higher fidelity, lower saving vs default).

Tiering (Freemium-style, no billing in stub):
- Set COMPRESSION_API_ENTERPRISE_KEYS to a comma-separated list of API tokens. Requests with
  X-API-Key: <token> or Authorization: Bearer <token> match → enterprise tier (Track A / active KPI).
- Missing or non-matching key → public tier (Track B / literal KPI estimate only; live evaluate_report suppressed).

POST /v1/metering/log appends one JSONL row (scripts/core/billing_meter.py); env TRACK_A_METERING_LOG_PATH overrides path.
Production SLA and payment are out of scope for this stub; see P0_COMMERCIALIZATION_TRACKER.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from scripts.core.billing_meter import append_meter_event  # noqa: E402
from scripts.core.compression_hardening_v1 import (  # noqa: E402
    extract_mask_must_keep,
    force_identity_on_eval_error,
    gatekeeper_bypass_max_tokens,
    llm_decode_params,
    should_bypass_compression,
    should_circuit_break_report,
)
from scripts.core.fallback_event_meter import append_fallback_event  # noqa: E402
from scripts.core.domain_router import DomainSpecificRouter  # noqa: E402
from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy  # noqa: E402
from scripts.core.secure_payload_keyring import (  # noqa: E402
    EnvTrackKeyResolver,
    ExternalKmsTrackKeyResolver,
    TrackKeyResolver,
)
from scripts.core.secure_payload_envelope_v1 import (  # noqa: E402
    AesGcmProvider,
    SCHEMA_NAME as SECURE_ENVELOPE_SCHEMA_NAME,
    SecurePayloadEnvelope,
    decrypt_envelope,
    encrypt_envelope,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.l1_side_channel_wire_codec import (  # noqa: E402
    decode_adaptive_msgpack,
    encode_adaptive_msgpack,
    minimal_payload,
)
from scripts.run_hybrid_codec_v0_spike import (  # noqa: E402
    decode_packet_dict as hybrid_decode_packet_dict,
)
from scripts.run_hybrid_codec_v0_spike import (  # noqa: E402
    encode_packet_dict as hybrid_encode_packet_dict,
)

API_CONTRACT_VERSION = "1.0.0"

SHARDS = ROOT / "codebook" / "shards"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
_router = DomainSpecificRouter(SHARDS)
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")
FALLBACK_PROFILE = (
    ROOT / "docs" / "final" / "artifacts" / "fallback_trigger_threshold_profile_latest.json"
)

app = FastAPI(title="MKM Token Compression Stub", version="1.0.0")

# Local dev / Explorer HTML: browser fetch from another origin or file://. Not a production CORS policy.
_cors_raw = os.environ.get("COMPRESSION_API_CORS_ALLOW_ORIGINS", "*").strip()
_cors_origins = ["*"] if _cors_raw in {"", "*"} else [x.strip() for x in _cors_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvalContext(BaseModel):
    eval_input_relative_path: str | None = None
    runner_hint: str | None = None
    notes: str | None = None
    hydrate_metrics: bool | None = None
    hydrate_live_eval: bool | None = None
    hydrate_shadow_compare: bool | None = None
    meter_log: bool | None = None
    emit_semantic_pointer: bool | None = None


class HydrationHints(BaseModel):
    atom_ids: list[str] | None = None


class CompressRequest(BaseModel):
    text: str
    locale: str | None = None
    client_request_id: str | None = None
    eval_context: EvalContext | None = None
    hydration_hints: HydrationHints | None = None


class CompressionMetrics(BaseModel):
    bytes_in: int
    bytes_out: int
    token_in: int | None = None
    token_out: int | None = None
    savings_ratio: float | None = None


class CompressResponse(BaseModel):
    api_contract_version: str = API_CONTRACT_VERSION
    schema_version: str = "token_compression_stub_v1"
    shard_id: str
    domain: str
    router_only: bool = True
    original_text: str
    client_request_id: str | None = None
    eval_context_echo: EvalContext | None = None
    compression_metrics: CompressionMetrics | None = None
    semantic_pointer: dict[str, Any] | None = None
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class ExpandRequest(BaseModel):
    payload: dict[str, Any]


class ExpandResponse(BaseModel):
    text: str
    api_contract_version: str = API_CONTRACT_VERSION
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class MeteringLogRequest(BaseModel):
    sla_track: str
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    client_request_id: str | None = None
    saving_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    measured_within_target_band_40_50: bool | None = None
    domain: str | None = None
    shard_id: str | None = None
    o200k_tokens_before: int | None = Field(default=None, ge=0)
    o200k_tokens_after: int | None = Field(default=None, ge=0)
    notes: str | None = None


class MeteringLogResponse(BaseModel):
    accepted: bool = True
    api_contract_version: str = API_CONTRACT_VERSION
    meter_schema: str = "track_a_metering_log_v1"
    log_path_relative: str | None = None


class L1SideChannelWireRequest(BaseModel):
    side_channel: dict[str, Any]
    track: str = Field(default="b_track")
    key_id: str | None = None
    zstd_min_raw_bytes: int = Field(default=64, ge=0)
    zstd_level: int = Field(default=3, ge=1, le=22)


class L1SideChannelWireResponse(BaseModel):
    envelope_schema: str = Field(default="l1_side_channel_secure_wire_v1", alias="schema")
    envelope: dict[str, Any]
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class _AesGcmCryptographyProvider(AesGcmProvider):
    """AES-256-GCM provider using cryptography package.

    Key injection policy:
    - A track: MKM_ENVELOPE_A_TRACK_KEY_B64
    - B track: MKM_ENVELOPE_B_TRACK_KEY_B64
    """

    def __init__(self, resolver: TrackKeyResolver | None = None) -> None:
        self._resolver = resolver or _select_track_key_resolver()

    def encrypt(
        self,
        *,
        key_id: str,
        plaintext: bytes,
        aad: bytes,
        track: str,
    ) -> tuple[bytes, bytes, bytes]:
        _ = key_id
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except Exception as exc:
            raise RuntimeError("cryptography package is required for secure envelope AES-GCM") from exc
        key = self._resolver.resolve_key(track=track)
        nonce = os.urandom(12)
        ct_plus_tag = AESGCM(key).encrypt(nonce, plaintext, aad)
        ciphertext, tag = ct_plus_tag[:-16], ct_plus_tag[-16:]
        return nonce, ciphertext, tag

    def decrypt(
        self,
        *,
        key_id: str,
        nonce: bytes,
        ciphertext: bytes,
        tag: bytes,
        aad: bytes,
        track: str,
    ) -> bytes:
        _ = key_id
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except Exception as exc:
            raise RuntimeError("cryptography package is required for secure envelope AES-GCM") from exc
        key = self._resolver.resolve_key(track=track)
        return AESGCM(key).decrypt(nonce, ciphertext + tag, aad)


def _default_key_id(track: str) -> str:
    if track == "a_track":
        return os.environ.get("MKM_ENVELOPE_A_TRACK_KEY_ID", "kms/a-track/primary")
    return os.environ.get("MKM_ENVELOPE_B_TRACK_KEY_ID", "kms/b-track/primary")


def _select_track_key_resolver() -> TrackKeyResolver:
    provider = os.environ.get("MKM_ENVELOPE_KEY_PROVIDER", "env").strip().lower()
    if provider in {"", "env"}:
        return EnvTrackKeyResolver()
    if provider in {"external_kms", "vault", "kms"}:
        return ExternalKmsTrackKeyResolver()
    raise RuntimeError(f"unsupported MKM_ENVELOPE_KEY_PROVIDER={provider!r}")


def _secure_key_provider_mode() -> str:
    return os.environ.get("MKM_ENVELOPE_KEY_PROVIDER", "env").strip().lower() or "env"


@lru_cache(maxsize=1)
def _decision_selected_saving_ratio() -> float | None:
    if not DECISION.is_file():
        return None
    try:
        doc = json.loads(DECISION.read_text(encoding="utf-8"))
    except Exception:
        return None
    selected = doc.get("selected_candidate", {})
    raw = selected.get("global_token_saving_rate")
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val < 0.0 or val > 1.0:
        return None
    return val


@lru_cache(maxsize=1)
def _decision_selected_profile() -> dict[str, Any]:
    if not DECISION.is_file():
        return {}
    try:
        doc = json.loads(DECISION.read_text(encoding="utf-8"))
    except Exception:
        return {}
    selected = doc.get("selected_candidate", {})
    return selected if isinstance(selected, dict) else {}


@lru_cache(maxsize=1)
def _baseline_avg_jaccard() -> float:
    if not BASELINE_V2.is_file():
        return 0.0
    try:
        base_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    except Exception:
        return 0.0
    return float(base_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))


KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"


@lru_cache(maxsize=1)
def _kpi_summary_snapshot() -> tuple[float | None, float | None, float | None, str | None]:
    """(literal global_token_saving_rate, active global_token_saving_rate, ultra_literal rate, ts_utc)."""
    if not KPI_SUMMARY.is_file():
        return None, None, None, None
    try:
        doc = json.loads(KPI_SUMMARY.read_text(encoding="utf-8"))
    except Exception:
        return None, None, None, None
    ts = doc.get("ts_utc")
    ts_s = str(ts) if ts is not None else None
    lit = doc.get("literal_kpi") or {}
    act = doc.get("active_kpi") or {}
    ultra = doc.get("ultra_literal_kpi") or {}
    lr = lit.get("global_token_saving_rate")
    ar = act.get("global_token_saving_rate")
    ur = ultra.get("global_token_saving_rate")
    try:
        lr_f = float(lr) if lr is not None else None
    except (TypeError, ValueError):
        lr_f = None
    try:
        ar_f = float(ar) if ar is not None else None
    except (TypeError, ValueError):
        ar_f = None
    try:
        ur_f = float(ur) if ur is not None else None
    except (TypeError, ValueError):
        ur_f = None
    return lr_f, ar_f, ur_f, ts_s


def _enterprise_key_list() -> list[str]:
    raw = os.environ.get("COMPRESSION_API_ENTERPRISE_KEYS", "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


@lru_cache(maxsize=1)
def _live_eval_min_tokens() -> int:
    """Minimum input token count to run live eval for enterprise hydration."""
    raw = os.environ.get("COMPRESSION_API_LIVE_EVAL_MIN_TOKENS", "12").strip()
    try:
        val = int(raw)
    except ValueError:
        return 12
    return max(0, val)


@lru_cache(maxsize=1)
def _hybrid_codec_v0_enabled() -> bool:
    force_off = os.environ.get("COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0", "").strip().lower()
    if force_off in {"1", "true", "yes", "on"}:
        return False
    raw = os.environ.get("COMPRESSION_API_USE_HYBRID_CODEC_V0", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    # Canary default-on: env unset means enabled.
    return True


def _tracka_profile_label() -> str:
    lane = os.environ.get("HYBRID_CODEC_TRACKA_DEFAULT_LANE", "").strip().lower()
    if lane:
        return f"{lane}_default"
    return "c3_domain_gated_default"


def _tracka_profile_source() -> str:
    lane = os.environ.get("HYBRID_CODEC_TRACKA_DEFAULT_LANE", "").strip().lower()
    if lane:
        return "env_tracka_default_lane"
    return "default_promoted"


def _resolve_tier(request: Request) -> str:
    """public | enterprise — enterprise only if key matches COMPRESSION_API_ENTERPRISE_KEYS."""
    keys = _enterprise_key_list()
    if not keys:
        # Legacy single-track: no keys configured → treat all requests as enterprise (CI/local parity).
        return "enterprise"
    x_key = (request.headers.get("x-api-key") or "").strip()
    auth = (request.headers.get("authorization") or "").strip()
    bearer = ""
    if auth.lower().startswith("bearer "):
        bearer = auth[7:].strip()
    token = x_key or bearer
    if token and token in keys:
        return "enterprise"
    return "public"


def _text_size_tokens(text: str) -> tuple[int, int]:
    """Return (bytes_in, token_in) once so callers can avoid duplicate regex scans."""
    return len(text.encode("utf-8")), len(TOKEN_RE.findall(text))


@lru_cache(maxsize=1)
def _fallback_profile_doc() -> dict[str, Any]:
    raw = os.environ.get("COMPRESSION_API_FALLBACK_PROFILE_PATH", "").strip()
    path = Path(raw) if raw else FALLBACK_PROFILE
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _fallback_signals(text: str) -> dict[str, float]:
    toks = TOKEN_RE.findall(text)
    n = max(1, len(toks))
    word_like = sum(1 for t in toks if re.fullmatch(r"[A-Za-z0-9_가-힣]+", t))
    symbol_like = n - word_like
    typo_like = sum(1 for t in toks if re.search(r"(.)\1\1", t))
    unknown_rate = symbol_like / n
    typo_ratio = typo_like / n
    # For this stub, OOV proxy follows unknown/symbol-heavy token ratio.
    oov_ratio = unknown_rate
    noise_mode_score = max(unknown_rate, min(1.0, typo_ratio * 2.0))
    return {
        "oov_ratio": oov_ratio,
        "typo_ratio": typo_ratio,
        "unknown_token_rate": unknown_rate,
        "detected_noise_mode": noise_mode_score,
    }


def _fallback_decision(text: str, token_in: int) -> tuple[bool, list[str], dict[str, float]]:
    doc = _fallback_profile_doc()
    sig = _fallback_signals(text)
    signals_cfg = (doc.get("signals") or {}) if isinstance(doc, dict) else {}
    reasons: list[str] = []
    try:
        if token_in > float(signals_cfg.get("input_tokens_threshold", 8000)):
            reasons.append("input_tokens_threshold")
        if sig["oov_ratio"] > float(signals_cfg.get("oov_ratio_threshold", 0.15)):
            reasons.append("oov_ratio_threshold")
        if sig["typo_ratio"] > float(signals_cfg.get("typo_ratio_threshold", 0.05)):
            reasons.append("typo_ratio_threshold")
        if sig["unknown_token_rate"] > float(signals_cfg.get("unknown_token_rate_threshold", 0.15)):
            reasons.append("unknown_token_rate_threshold")
        if sig["detected_noise_mode"] > float(signals_cfg.get("detected_noise_mode_threshold", 0.5)):
            reasons.append("detected_noise_mode_threshold")
    except Exception:
        # Fail-open to conservative fallback when profile is malformed.
        reasons.append("fallback_profile_parse_error")
    return bool(reasons), reasons, sig


def _estimate_metrics_from_text(
    text: str, savings_ratio: float, *, bytes_in: int | None = None, token_in: int | None = None
) -> CompressionMetrics:
    if bytes_in is None or token_in is None:
        bytes_in, token_in = _text_size_tokens(text)
    token_out = max(1, int(round(token_in * (1.0 - savings_ratio)))) if token_in > 0 else 0
    # Convert token proxy back to byte estimate using input average bytes/token.
    avg_bpt = (bytes_in / token_in) if token_in > 0 else 0.0
    bytes_out = int(round(token_out * avg_bpt)) if token_out > 0 else 0
    return CompressionMetrics(
        bytes_in=bytes_in,
        bytes_out=bytes_out,
        token_in=token_in,
        token_out=token_out,
        savings_ratio=savings_ratio,
    )


def _estimate_hydrated_metrics(text: str) -> CompressionMetrics | None:
    ratio = _decision_selected_saving_ratio()
    if ratio is None:
        return None
    return _estimate_metrics_from_text(text, ratio)


def _live_eval_metrics(
    text: str,
    *,
    bytes_in: int | None = None,
    token_in: int | None = None,
    emit_semantic_pointer: bool = False,
    extra_must_keep: set[str] | None = None,
) -> tuple[CompressionMetrics | None, float, str | None, dict[str, Any] | None]:
    selected = _decision_selected_profile()
    strategy = str(selected.get("strategy", "A"))
    intensity = str(selected.get("intensity", "extreme"))
    general_cap = selected.get("general_max_saving_rate")
    sensitive_cap = selected.get("sensitive_max_saving_rate")
    hangul_cap = selected.get("hangul_max_saving_rate")
    t0 = perf_counter()
    doc = {
        "compression_cases": [
            {"id": "api-live", "raw_text": text, "compressed_text": "", "reconstructed_text": ""}
        ],
        "fusion_answer_cases": [],
    }
    mk = {"사상의학", "체질", "sasang", "myeongri", "bible"}
    if extra_must_keep:
        mk = mk | set(extra_must_keep)
    try:
        _bp = env_apply_gematria_4d_bridge_policy()
        report = evaluate_report(
            doc,
            source_input="api:live_eval",
            mode="experimental",
            strategy=strategy if strategy in {"A", "B", "C"} else "A",
            intensity=intensity if intensity in {"high", "ultra", "extreme"} else "extreme",
            must_keep=mk,
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
        cb_on, cb_reasons = should_circuit_break_report(report)
        if cb_on:
            return None, (perf_counter() - t0) * 1000.0, "circuit_breaker:" + ",".join(cb_reasons), None
        comp_block = report.get("compression_metrics", {})
        ratio = float(comp_block.get("global_token_saving_rate", 0.0))
        cases = comp_block.get("cases", [])
        if bytes_in is None or token_in is None:
            bytes_in, token_in = _text_size_tokens(text)
        bytes_out: int
        token_out: int
        if isinstance(cases, list) and cases:
            first = cases[0] if isinstance(cases[0], dict) else {}
            effective = str(first.get("compressed_text_effective", ""))
            bytes_out = len(effective.encode("utf-8"))
            token_out = len(TOKEN_RE.findall(effective))
            # Keep non-zero lower bound for non-empty input if compressed text was empty unexpectedly.
            if bytes_in > 0 and bytes_out == 0:
                bytes_out = 1
        else:
            # Fallback when report shape is unexpected.
            est = _estimate_metrics_from_text(
                text, max(0.0, min(1.0, ratio)), bytes_in=bytes_in, token_in=token_in
            )
            bytes_out = est.bytes_out
            token_out = int(est.token_out or 0)
        metrics = CompressionMetrics(
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            token_in=token_in,
            token_out=token_out,
            savings_ratio=max(0.0, min(1.0, ratio)),
        )
        sp0: dict[str, Any] | None = None
        if emit_semantic_pointer and isinstance(cases, list) and cases:
            first_row = cases[0]
            if isinstance(first_row, dict):
                cand = first_row.get("semantic_pointer")
                if isinstance(cand, dict):
                    sp0 = cand
        return metrics, round((perf_counter() - t0) * 1000.0, 3), None, sp0
    except Exception as exc:
        if force_identity_on_eval_error():
            return (
                None,
                round((perf_counter() - t0) * 1000.0, 3),
                f"circuit_breaker_eval_error:{type(exc).__name__}",
                None,
            )
        return None, round((perf_counter() - t0) * 1000.0, 3), type(exc).__name__, None


def _try_append_meter_from_compress(
    *,
    metrics: CompressionMetrics | None,
    flags: dict[str, Any],
    client_request_id: str | None,
    sla_track: str,
    domain: str,
    shard_id: str,
) -> None:
    """Optional JSONL row when eval_context.meter_log is true and token counts exist."""
    if metrics is None:
        flags["meter_log_skipped"] = "no_compression_metrics"
        return
    tin, tout = metrics.token_in, metrics.token_out
    if tin is None or tout is None:
        flags["meter_log_skipped"] = "missing_token_in_or_token_out"
        return
    evt: dict[str, Any] = {
        "sla_track": sla_track,
        "tokens_before": int(tin),
        "tokens_after": int(tout),
        "client_request_id": client_request_id,
        "domain": domain,
        "shard_id": shard_id,
        "notes": "from_compress_eval_context_meter_log",
    }
    if metrics.savings_ratio is not None:
        evt["saving_rate"] = max(0.0, min(1.0, float(metrics.savings_ratio)))
    try:
        append_meter_event(evt)
        flags["meter_log_appended"] = True
    except Exception as exc:
        flags["meter_log_append_failed"] = True
        flags["meter_log_append_error_class"] = type(exc).__name__


@app.post("/v1/metering/log", response_model=MeteringLogResponse)
def metering_log(body: MeteringLogRequest) -> MeteringLogResponse:
    """Append one metering row (JSONL). Override path via env TRACK_A_METERING_LOG_PATH."""
    res = append_meter_event(body.model_dump(exclude_none=True))
    return MeteringLogResponse(
        accepted=bool(res.get("accepted")),
        meter_schema=str(res.get("meter_schema") or "track_a_metering_log_v1"),
        log_path_relative=res.get("log_path_relative"),
    )


@app.get("/health")
def health() -> dict[str, Any]:
    lit_r, act_r, ultra_r, ts_utc = _kpi_summary_snapshot()
    keys_on = bool(_enterprise_key_list())
    return {
        "status": "ok",
        "api_contract_version": API_CONTRACT_VERSION,
        "schema_version": "token_compression_stub_v1",
        "tier_policy": {
            "public_sla_track": "literal",
            "enterprise_sla_track": "active",
            "enterprise_keys_configured": keys_on,
        },
        "tracka_profile": _tracka_profile_label(),
        "tracka_profile_source": _tracka_profile_source(),
        "kpi_snapshot": {
            "source_relative": "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json",
            "ts_utc": ts_utc,
            "literal_global_token_saving_rate": lit_r,
            "active_global_token_saving_rate": act_r,
            "ultra_literal_global_token_saving_rate": ultra_r,
        },
        "secure_envelope": {
            "schema": SECURE_ENVELOPE_SCHEMA_NAME,
            "tracks": ["a_track", "b_track"],
            "key_provider_mode": _secure_key_provider_mode(),
            "key_env": {
                "a_track": "MKM_ENVELOPE_A_TRACK_KEY_B64",
                "b_track": "MKM_ENVELOPE_B_TRACK_KEY_B64",
            },
        },
    }


@app.post("/v1/compress", response_model=CompressResponse)
def compress(body: CompressRequest, request: Request) -> CompressResponse:
    tier = _resolve_tier(request)
    route = _router.route(body.text)
    lit_r, act_r, ultra_r, _k_ts = _kpi_summary_snapshot()
    literal_rate = float(lit_r) if lit_r is not None else 0.24613220815752457
    ultra_literal_rate = float(ultra_r) if ultra_r is not None else 0.13220815752461323
    active_rate = float(act_r) if act_r is not None else (_decision_selected_saving_ratio() or 0.49)

    flags: dict[str, Any] = {
        "hangul_principle": route.hangul_principle,
        "hard_keep_count": len(route.must_keep_hard_terms),
        "soft_keep_count": len(route.must_keep_soft_terms),
        "tier": tier,
        "sla_track": "literal" if tier == "public" else "active",
        "tracka_profile": _tracka_profile_label(),
        "tracka_profile_source": _tracka_profile_source(),
    }
    hybrid_payload: dict[str, Any] | None = None
    if _hybrid_codec_v0_enabled():
        try:
            hybrid_payload = hybrid_encode_packet_dict(body.text)
            restored = hybrid_decode_packet_dict(hybrid_payload)
            hybrid_saving = 1.0 - (
                float(hybrid_payload["output_char_len"]) / max(1.0, float(hybrid_payload["input_char_len"]))
            )
            flags["hybrid_codec_v0_enabled"] = True
            flags["hybrid_codec_v0_payload"] = hybrid_payload
            flags["hybrid_codec_v0_exact_restore_ok"] = restored == body.text
            flags["hybrid_codec_v0_checksum_ok"] = True
            flags["hybrid_codec_v0_saving_rate_chars"] = hybrid_saving
        except Exception as exc:
            flags["hybrid_codec_v0_enabled"] = True
            flags["hybrid_codec_v0_failed"] = True
            flags["hybrid_codec_v0_error_class"] = type(exc).__name__
    live_metrics_cache: (
        tuple[CompressionMetrics | None, float, str | None, dict[str, Any] | None] | None
    ) = None
    bytes_in, token_in = _text_size_tokens(body.text)
    mask_terms, mask_meta = extract_mask_must_keep(body.text)
    if mask_meta.get("mask_applied"):
        flags["precompress_mask"] = mask_meta
    flags["llm_decode_params"] = llm_decode_params()
    flags["compression_hardening_config"] = "compression_enterprise_hardening_config_v1.json"
    if should_bypass_compression(token_in):
        flags["compression_gatekeeper_bypass"] = True
        flags["compression_gatekeeper_max_tokens"] = gatekeeper_bypass_max_tokens()
        metrics = _estimate_metrics_from_text(body.text, 0.0, bytes_in=bytes_in, token_in=token_in)
        flags["metrics_mode"] = "identity_gatekeeper_bypass"
        flags["shadow_mode"] = "disabled"
        return CompressResponse(
            shard_id=route.shard_id,
            domain=route.domain,
            original_text=body.text,
            client_request_id=body.client_request_id,
            eval_context_echo=body.eval_context,
            compression_metrics=metrics,
            semantic_pointer=None,
            integrity_flags=flags,
        )
    fallback_on, fallback_reasons, fallback_sig = _fallback_decision(body.text, token_in)
    flags["fallback_profile_active"] = bool(_fallback_profile_doc())
    flags["fallback_safe_triggered"] = fallback_on
    flags["fallback_trigger_reasons"] = fallback_reasons
    flags["fallback_signal_snapshot"] = fallback_sig
    if body.hydration_hints is not None and body.hydration_hints.atom_ids:
        flags["hydration_atom_id_count"] = len(body.hydration_hints.atom_ids)
    try:
        evt = {
            "triggered": fallback_on,
            "tier": tier,
            "reasons": fallback_reasons,
            "signals": fallback_sig,
            "input_tokens": token_in,
            "input_bytes": bytes_in,
            "client_request_id": body.client_request_id,
            "domain": route.domain,
            "shard_id": route.shard_id,
        }
        fres = append_fallback_event(evt)
        flags["fallback_event_logged"] = bool(fres.get("accepted"))
    except Exception as exc:
        flags["fallback_event_log_failed"] = True
        flags["fallback_event_log_error_class"] = type(exc).__name__

    # --- Public: Track B (literal KPI estimate only; no live evaluate_report ---
    if tier == "public":
        runner_hint = (
            str(body.eval_context.runner_hint).strip().lower()
            if body.eval_context is not None and body.eval_context.runner_hint
            else ""
        )
        use_ultra_literal = runner_hint in {"ultra_literal", "ultra-literal", "precision_first"}
        public_ratio = ultra_literal_rate if use_ultra_literal else literal_rate
        metrics = _estimate_metrics_from_text(body.text, public_ratio, bytes_in=bytes_in, token_in=token_in)
        flags["sla_track"] = "ultra_literal" if use_ultra_literal else "literal"
        flags["metrics_mode"] = "ultra_literal_kpi_estimate" if use_ultra_literal else "literal_kpi_estimate"
        if body.eval_context is not None and bool(body.eval_context.hydrate_live_eval):
            flags["hydrate_live_eval_suppressed"] = True
            flags["hydrate_live_eval_suppressed_reason"] = "public_tier_use_enterprise_key"
        flags["shadow_mode"] = "disabled"
        if body.eval_context is not None and bool(body.eval_context.meter_log):
            _try_append_meter_from_compress(
                metrics=metrics,
                flags=flags,
                client_request_id=body.client_request_id,
                sla_track=str(flags.get("sla_track") or "literal"),
                domain=route.domain,
                shard_id=route.shard_id,
            )
        return CompressResponse(
            shard_id=route.shard_id,
            domain=route.domain,
            original_text=body.text,
            client_request_id=body.client_request_id,
            eval_context_echo=body.eval_context,
            compression_metrics=metrics,
            semantic_pointer=None,
            integrity_flags=flags,
        )

    # --- Enterprise: Track A (existing hydration + default active KPI when no hydration) ---
    metrics: CompressionMetrics | None = None
    metrics_mode = "none"
    semantic_pointer_out: dict[str, Any] | None = None
    emit_sp = bool(body.eval_context is not None and bool(body.eval_context.emit_semantic_pointer))
    if body.eval_context is not None and bool(body.eval_context.hydrate_metrics):
        live_eval_requested = bool(body.eval_context.hydrate_live_eval)
        if fallback_on and live_eval_requested:
            flags["hydrate_live_eval_suppressed"] = True
            flags["hydrate_live_eval_suppressed_reason"] = "fallback_safe_triggered"
        allow_live_eval = live_eval_requested and (not fallback_on)
        if allow_live_eval:
            min_tok = _live_eval_min_tokens()
            if token_in >= min_tok:
                metrics, latency_ms, live_err, sp_live = _live_eval_metrics(
                    body.text,
                    bytes_in=bytes_in,
                    token_in=token_in,
                    emit_semantic_pointer=emit_sp,
                    extra_must_keep=mask_terms,
                )
                live_metrics_cache = (metrics, latency_ms, live_err, sp_live)
                flags["hydration_live_eval_elapsed_ms"] = latency_ms
                if live_err:
                    flags["hydration_live_eval_failed"] = True
                    flags["hydration_live_eval_error_class"] = live_err
                if metrics is not None:
                    flags["hydration_metrics_source"] = "live_evaluate_report"
                    metrics_mode = "live"
                if sp_live is not None:
                    semantic_pointer_out = sp_live
            else:
                flags["hydration_live_eval_skipped"] = True
                flags["hydration_live_eval_skip_reason"] = "short_input"
                flags["hydration_live_eval_min_tokens"] = min_tok
        if metrics is None:
            metrics = _estimate_hydrated_metrics(body.text)
            if metrics is None:
                flags["hydration_metrics_unavailable"] = True
            else:
                flags["hydration_metrics_source"] = "decision_selected_candidate"
                metrics_mode = "decision_fallback"
    else:
        # Default compress: shard + routing only; metrics only when hydrate_metrics is set (OpenAPI mode_none).
        metrics = None
        metrics_mode = "none"

    if body.eval_context is not None and bool(body.eval_context.hydrate_shadow_compare):
        if live_metrics_cache is not None:
            # Avoid duplicate evaluate_report call in the same request when live hydration already ran.
            shadow_metrics, shadow_latency_ms, shadow_err, shadow_sp = live_metrics_cache
            flags["shadow_live_eval_reused_from_hydration"] = True
            if semantic_pointer_out is None and shadow_sp is not None:
                semantic_pointer_out = shadow_sp
        else:
            shadow_metrics, shadow_latency_ms, shadow_err, shadow_sp = _live_eval_metrics(
                body.text,
                bytes_in=bytes_in,
                token_in=token_in,
                emit_semantic_pointer=emit_sp,
                extra_must_keep=mask_terms,
            )
            if semantic_pointer_out is None and shadow_sp is not None:
                semantic_pointer_out = shadow_sp
        flags["shadow_mode"] = "enabled"
        flags["shadow_elapsed_ms"] = shadow_latency_ms
        if shadow_err:
            flags["shadow_live_eval_failed"] = True
            flags["shadow_live_eval_error_class"] = shadow_err
        if shadow_metrics is not None:
            flags["shadow_metrics_mode"] = "live"
            flags["shadow_savings_ratio"] = shadow_metrics.savings_ratio
        else:
            flags["shadow_metrics_mode"] = "none"
    else:
        flags["shadow_mode"] = "disabled"
    flags["metrics_mode"] = metrics_mode
    if body.eval_context is not None and bool(body.eval_context.meter_log):
        _try_append_meter_from_compress(
            metrics=metrics,
            flags=flags,
            client_request_id=body.client_request_id,
            sla_track=str(flags.get("sla_track") or "active"),
            domain=route.domain,
            shard_id=route.shard_id,
        )
    return CompressResponse(
        shard_id=route.shard_id,
        domain=route.domain,
        original_text=body.text,
        client_request_id=body.client_request_id,
        eval_context_echo=body.eval_context,
        compression_metrics=metrics,
        semantic_pointer=semantic_pointer_out,
        integrity_flags=flags,
    )


@app.post("/v1/expand", response_model=ExpandResponse)
def expand(body: ExpandRequest) -> ExpandResponse:
    payload = body.payload
    text = str(payload.get("original_text") or payload.get("text") or "")
    try:
        candidate = payload.get("hybrid_codec_v0_payload")
        if isinstance(candidate, dict):
            text = hybrid_decode_packet_dict(candidate)
        elif str(payload.get("schema") or "") == "hybrid_codec_v0_payload_v1":
            text = hybrid_decode_packet_dict(payload)
    except Exception as exc:
        return ExpandResponse(
            text=text,
            integrity_flags={
                "stub_expand": True,
                "lossless_echo": False,
                "hybrid_codec_v0_expand_failed": True,
                "hybrid_codec_v0_expand_error_class": type(exc).__name__,
            },
        )
    return ExpandResponse(
        text=text,
        integrity_flags={"stub_expand": True, "lossless_echo": True},
    )


@app.post("/v1/research/l1_side_channel/wire/secure", response_model=L1SideChannelWireResponse)
def encode_l1_side_channel_secure_wire(body: L1SideChannelWireRequest) -> L1SideChannelWireResponse:
    """Research lane: side-channel -> adaptive msgpack wire -> AES-256-GCM envelope."""
    if body.track not in {"a_track", "b_track"}:
        return L1SideChannelWireResponse(
            envelope={},
            integrity_flags={
                "research_lane": True,
                "secure_envelope": True,
                "error": "invalid_track",
            },
        )
    try:
        minimal = minimal_payload(body.side_channel)
    except Exception as exc:
        return L1SideChannelWireResponse(
            envelope={},
            integrity_flags={
                "research_lane": True,
                "secure_envelope": True,
                "error": "invalid_side_channel_payload",
                "error_class": type(exc).__name__,
            },
        )
    try:
        wire_bytes, variant = encode_adaptive_msgpack(
            minimal,
            zstd_min_raw_bytes=body.zstd_min_raw_bytes,
            zstd_level=body.zstd_level,
        )
        # decode sanity check to detect malformed wire implementation regressions
        _decoded = decode_adaptive_msgpack(wire_bytes)
    except Exception as exc:
        return L1SideChannelWireResponse(
            envelope={},
            integrity_flags={
                "research_lane": True,
                "secure_envelope": True,
                "error": "wire_encode_failed",
                "error_class": type(exc).__name__,
            },
        )
    try:
        provider = _AesGcmCryptographyProvider()
    except Exception as exc:
        return L1SideChannelWireResponse(
            envelope={},
            integrity_flags={
                "research_lane": True,
                "secure_envelope": True,
                "error": "secure_envelope_encrypt_failed",
                "error_class": type(exc).__name__,
            },
        )
    key_id = body.key_id or _default_key_id(body.track)
    codec_variant = "zstd_msgpack" if variant == "zstd" else "raw_msgpack"
    try:
        envelope = encrypt_envelope(
            provider=provider,
            key_id=key_id,
            track=body.track,
            codec_variant=codec_variant,
            payload_bytes=wire_bytes,
        )
        # runtime tamper/auth contract smoke: decrypt must succeed immediately
        _payload = decrypt_envelope(provider=provider, envelope=envelope)
        assert _payload == wire_bytes
    except Exception as exc:
        return L1SideChannelWireResponse(
            envelope={},
            integrity_flags={
                "research_lane": True,
                "secure_envelope": True,
                "error": "secure_envelope_encrypt_failed",
                "error_class": type(exc).__name__,
            },
        )
    return L1SideChannelWireResponse(
        envelope=SecurePayloadEnvelope(
            schema=envelope.schema,
            header=envelope.header,
            aad_b64=envelope.aad_b64,
            nonce_b64=envelope.nonce_b64,
            ciphertext_b64=envelope.ciphertext_b64,
            tag_b64=envelope.tag_b64,
        ).to_dict(),
        integrity_flags={
            "research_lane": True,
            "secure_envelope": True,
            "aes_gcm_256": True,
            "track": body.track,
            "codec_variant": codec_variant,
            "wire_payload_bytes": len(wire_bytes),
        },
    )
