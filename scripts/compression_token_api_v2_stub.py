#!/usr/bin/env python3
"""FastAPI v2 draft: Trust Packet round-trip (openapi_token_compression_v2_draft.yaml, Fact-Lock §11).

Run: uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011

Compress uses ``evaluate_report`` (same family as v1 live hydration). The packet's ``residual_meta``
includes ``mk_stub_v2.reconstructed_text`` so ``POST /v2/expand`` can return engine reconstruction
without echoing a separate v1 ``original_text`` field — still experimental, not a production SLA.
``GlobalPivotCompressionPipeline`` is not used; name in early drafts was superseded by this path.
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
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

API_CONTRACT_VERSION = "2.0.0-draft"
PACKET_FORMAT_VERSION = "trust_packet.0.1"
RESIDUAL_STUB_KEY = "mk_stub_v2"

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


class ExpandRequestV2(BaseModel):
    compression_packet: CompressionPacket


class ExpandResponseV2(BaseModel):
    text: str
    api_contract_version: str = API_CONTRACT_VERSION
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


def _token_count_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _run_evaluate_for_packet(text: str, loss_profile: LossProfile) -> dict[str, Any]:
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
    # lossless_text: prefer reconstructed == raw for messaging (engine still experimental).
    out: dict[str, Any] = {
        "ok": True,
        "elapsed_ms": elapsed_ms,
        "compressed_text": comp,
        "reconstructed_text": rec if rec else text,
        "global_ratio": ratio,
        "jaccard": float(jac) if jac is not None else None,
    }
    if loss_profile == "lossless_text":
        out["integrity_note"] = "lossless_text_profile_engine_may_still_be_semantic_stub"
    elif loss_profile == "code_equivalent":
        out["integrity_note"] = "code_equivalent_profile_not_isolated_to_nitro_path_in_stub"
    return out


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "api_contract_version": API_CONTRACT_VERSION,
        "packet_format_version": PACKET_FORMAT_VERSION,
        "schema_version": "token_compression_stub_v2_draft",
        "stub_engine": "evaluate_report",
    }


@app.post("/v2/compress", response_model=CompressResponseV2)
def compress_v2(body: CompressRequestV2) -> CompressResponseV2:
    route = _router.route(body.text)
    flags: dict[str, Any] = {
        "stub_v2": True,
        "hangul_principle": route.hangul_principle,
        "loss_profile": body.loss_profile,
    }
    try:
        ev = _run_evaluate_for_packet(body.text, body.loss_profile)
        flags["evaluate_report_ms"] = ev.get("elapsed_ms")
        if not ev.get("ok"):
            flags["evaluate_report_degraded"] = True
        if ev.get("jaccard") is not None:
            flags["jaccard_proxy"] = ev.get("jaccard")
        if ev.get("integrity_note"):
            flags["integrity_note"] = ev.get("integrity_note")
        rec = str(ev.get("reconstructed_text") or body.text)
        comp = str(ev.get("compressed_text") or body.text)
        residual_meta = {
            RESIDUAL_STUB_KEY: {
                "reconstructed_text": rec,
                "global_token_saving_rate": ev.get("global_ratio"),
                "reconstruction_fidelity_jaccard": ev.get("jaccard"),
            },
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
        ratio = ev.get("global_ratio")
        if ratio is None:
            sr = None
        else:
            sr = max(0.0, min(1.0, float(ratio)))
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
    flags: dict[str, Any] = {"stub_v2": True, "reassembly": "residual_meta"}
    meta = pkt.residual_meta or {}
    stub = meta.get(RESIDUAL_STUB_KEY) if isinstance(meta, dict) else None
    if isinstance(stub, dict) and "reconstructed_text" in stub:
        text = str(stub["reconstructed_text"])
        flags["source"] = RESIDUAL_STUB_KEY
        return ExpandResponseV2(text=text, integrity_flags=flags)
    # Degraded: return compressed_text with warning (no v1-style original echo field).
    flags["reassembly"] = "degraded_compressed_text_only"
    return ExpandResponseV2(text=pkt.compressed_text, integrity_flags=flags)
