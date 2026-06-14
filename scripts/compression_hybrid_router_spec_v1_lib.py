#!/usr/bin/env python3
"""Load corpus-tag → backend bindings from compression_hybrid_router_spec_v1.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"

SkuClass = Literal["coord", "mask"]


@dataclass
class HybridRouterResolution:
    corpus_tag: str
    sku_class: str | None
    binding: dict[str, Any]
    recommended_backend: str
    stub_can_apply_mkm: bool
    compression_profile: str | None = None
    routing_profile: str | None = None
    enable_candidate_pool_expansion: bool = False
    candidate_artifact: str | None = None
    short_context_token_threshold: int | None = None
    short_context_max_saving_rate: float | None = None
    must_keep_overlay_json: str | None = None
    overlay_terms: list[str] = field(default_factory=list)
    research_only: bool = True


@lru_cache(maxsize=1)
def load_hybrid_router_spec(spec_path: str | None = None) -> dict[str, Any]:
    path = Path(spec_path) if spec_path else DEFAULT_SPEC
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def list_corpus_bindings(*, spec_path: Path | None = None) -> list[dict[str, Any]]:
    spec = load_hybrid_router_spec(str(spec_path) if spec_path else None)
    rows = spec.get("corpus_bindings")
    return list(rows) if isinstance(rows, list) else []


def _match_binding(corpus_tag: str, bindings: list[dict[str, Any]]) -> dict[str, Any] | None:
    tag = corpus_tag.strip()
    for row in bindings:
        if not isinstance(row, dict):
            continue
        if str(row.get("corpus_tag") or "") == tag or str(row.get("corpus_id") or "") == tag:
            return row
    return None


def resolve_hybrid_router(
    corpus_tag: str | None,
    *,
    sku_class: SkuClass | None = None,
    workspace_root: Path = ROOT,
    spec_path: Path | None = None,
    load_overlay: bool = True,
) -> HybridRouterResolution | None:
    if not corpus_tag or not str(corpus_tag).strip():
        return None
    spec = load_hybrid_router_spec(str(spec_path) if spec_path else None)
    binding = _match_binding(str(corpus_tag).strip(), list_corpus_bindings(spec_path=spec_path or DEFAULT_SPEC))
    if binding is None:
        return None
    backend = str(binding.get("backend") or "")
    stub_mkm = (
        backend.startswith("mkm_v2")
        or backend.startswith("mkm_candidate")
        or backend.startswith("mkm_economy")
    )
    overlay_terms: list[str] = []
    overlay_rel = binding.get("must_keep_overlay_json")
    if load_overlay and isinstance(overlay_rel, str) and overlay_rel.strip():
        overlay_path = (workspace_root / overlay_rel).resolve()
        if overlay_path.is_file():
            from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms

            overlay_terms = load_overlay_terms(overlay_path)
    return HybridRouterResolution(
        corpus_tag=str(corpus_tag).strip(),
        sku_class=sku_class or str(binding.get("sku_class") or "SKU-MASK").replace("SKU-", "").lower(),
        binding=binding,
        recommended_backend=backend,
        stub_can_apply_mkm=stub_mkm,
        compression_profile=binding.get("compression_profile"),
        routing_profile=binding.get("routing_profile"),
        enable_candidate_pool_expansion=bool(binding.get("enable_candidate_pool_expansion")),
        candidate_artifact=binding.get("candidate_artifact"),
        short_context_token_threshold=binding.get("short_context_token_threshold"),
        short_context_max_saving_rate=binding.get("short_context_max_saving_rate"),
        must_keep_overlay_json=str(overlay_rel) if overlay_rel else None,
        overlay_terms=overlay_terms,
        research_only=bool(spec.get("research_only", True)),
    )


def corpus_binding_integrity_flags(res: HybridRouterResolution) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "hybrid_router_spec": DEFAULT_SPEC.relative_to(ROOT).as_posix(),
        "corpus_tag": res.corpus_tag,
        "sku_class": res.sku_class,
        "hybrid_router_backend_recommended": res.recommended_backend,
        "hybrid_router_stub_applies_mkm": res.stub_can_apply_mkm,
        "research_only": res.research_only,
    }
    if res.must_keep_overlay_json:
        flags["must_keep_overlay_json"] = res.must_keep_overlay_json
    if res.binding.get("kpi_saving_eligible") is False:
        flags["kpi_saving_eligible"] = False
    if res.routing_profile:
        flags["routing_profile_binding"] = res.routing_profile
    if res.enable_candidate_pool_expansion:
        flags["enable_candidate_pool_expansion_binding"] = True
    if res.candidate_artifact:
        flags["candidate_artifact"] = res.candidate_artifact
    return flags
