#!/usr/bin/env python3
"""FastAPI stub: domain router envelope only (FACT-LOCK alignment with openapi_token_compression_stub_v1.yaml).

Run: uvicorn scripts.compression_token_api_stub:app --host 127.0.0.1 --port 8010

Full token metrics require multilens eval (see run_ultra_compression_default.py).
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from scripts.core.domain_router import DomainSpecificRouter  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

API_CONTRACT_VERSION = "1.0.0"

SHARDS = ROOT / "codebook" / "shards"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
_router = DomainSpecificRouter(SHARDS)
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")

app = FastAPI(title="MKM Token Compression Stub", version="1.0.0")


class EvalContext(BaseModel):
    eval_input_relative_path: str | None = None
    runner_hint: str | None = None
    notes: str | None = None
    hydrate_metrics: bool | None = None
    hydrate_live_eval: bool | None = None
    hydrate_shadow_compare: bool | None = None


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
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


class ExpandRequest(BaseModel):
    payload: dict[str, Any]


class ExpandResponse(BaseModel):
    text: str
    api_contract_version: str = API_CONTRACT_VERSION
    integrity_flags: dict[str, Any] = Field(default_factory=dict)


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


def _estimate_metrics_from_text(text: str, savings_ratio: float) -> CompressionMetrics:
    bytes_in = len(text.encode("utf-8"))
    token_in = len(TOKEN_RE.findall(text))
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


def _live_eval_metrics(text: str) -> tuple[CompressionMetrics | None, float]:
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
    try:
        report = evaluate_report(
            doc,
            source_input="api:live_eval",
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
        comp_block = report.get("compression_metrics", {})
        ratio = float(comp_block.get("global_token_saving_rate", 0.0))
        cases = comp_block.get("cases", [])
        bytes_in = len(text.encode("utf-8"))
        token_in = len(TOKEN_RE.findall(text))
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
            est = _estimate_metrics_from_text(text, max(0.0, min(1.0, ratio)))
            bytes_out = est.bytes_out
            token_out = int(est.token_out or 0)
        metrics = CompressionMetrics(
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            token_in=token_in,
            token_out=token_out,
            savings_ratio=max(0.0, min(1.0, ratio)),
        )
        return metrics, round((perf_counter() - t0) * 1000.0, 3)
    except Exception:
        return None, round((perf_counter() - t0) * 1000.0, 3)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compress", response_model=CompressResponse)
def compress(body: CompressRequest) -> CompressResponse:
    route = _router.route(body.text)
    flags: dict[str, Any] = {
        "hangul_principle": route.hangul_principle,
        "hard_keep_count": len(route.must_keep_hard_terms),
        "soft_keep_count": len(route.must_keep_soft_terms),
    }
    if body.hydration_hints is not None and body.hydration_hints.atom_ids:
        flags["hydration_atom_id_count"] = len(body.hydration_hints.atom_ids)
    metrics: CompressionMetrics | None = None
    metrics_mode = "none"
    if body.eval_context is not None and bool(body.eval_context.hydrate_metrics):
        if bool(body.eval_context.hydrate_live_eval):
            metrics, latency_ms = _live_eval_metrics(body.text)
            flags["hydration_live_eval_elapsed_ms"] = latency_ms
            if metrics is not None:
                flags["hydration_metrics_source"] = "live_evaluate_report"
                metrics_mode = "live"
        if metrics is None:
            metrics = _estimate_hydrated_metrics(body.text)
            if metrics is None:
                flags["hydration_metrics_unavailable"] = True
            else:
                flags["hydration_metrics_source"] = "decision_selected_candidate"
                metrics_mode = "decision_fallback"
    if body.eval_context is not None and bool(body.eval_context.hydrate_shadow_compare):
        # Non-invasive shadow: evaluate live path for observability only.
        shadow_metrics, shadow_latency_ms = _live_eval_metrics(body.text)
        flags["shadow_mode"] = "enabled"
        flags["shadow_elapsed_ms"] = shadow_latency_ms
        if shadow_metrics is not None:
            flags["shadow_metrics_mode"] = "live"
            flags["shadow_savings_ratio"] = shadow_metrics.savings_ratio
        else:
            flags["shadow_metrics_mode"] = "none"
    else:
        flags["shadow_mode"] = "disabled"
    flags["metrics_mode"] = metrics_mode
    return CompressResponse(
        shard_id=route.shard_id,
        domain=route.domain,
        original_text=body.text,
        client_request_id=body.client_request_id,
        eval_context_echo=body.eval_context,
        compression_metrics=metrics,
        integrity_flags=flags,
    )


@app.post("/v1/expand", response_model=ExpandResponse)
def expand(body: ExpandRequest) -> ExpandResponse:
    payload = body.payload
    text = str(payload.get("original_text") or payload.get("text") or "")
    return ExpandResponse(
        text=text,
        integrity_flags={"stub_expand": True, "lossless_echo": True},
    )
