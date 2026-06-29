#!/usr/bin/env python3
"""[HYPO] B-track coding proxy surface + post-gatekeeper Prism meta sidecar."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "experiments" / "no_guard_limit_test"
DEFAULT_CONTRACT = SANDBOX / "prism_pinset_swap_contract_v1.json"
DEFAULT_REGISTRY = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"


def meta_channel_enabled() -> bool:
    raw = os.environ.get("MKM_PRISM_META_CHANNEL_BTRACK", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def build_meta_sidecar(
    text: str,
    *,
    lane: str | None = None,
    task_profile: str = "py_coding",
    selection_mode: str = "fixed_preferred",
) -> dict[str, Any]:
    from scripts.sandbox.build_prism_pinset_swap_v1 import (
        estimate_pinset_tokens,
        format_pinset_block,
        select_pinset,
    )

    pinset = select_pinset(
        registry_path=DEFAULT_REGISTRY,
        contract_path=DEFAULT_CONTRACT,
        task_profile=task_profile,
        context_text=text,
        file_hint=lane or "",
        selection_mode=selection_mode,
    )
    block = format_pinset_block(pinset)
    return {
        "research_only": True,
        "hypothesis_tier": "B",
        "pinset": pinset,
        "meta_channel_block": block,
        "meta_channel_tokens": estimate_pinset_tokens(block),
        "injection_mode": "meta_channel_post_gatekeeper",
    }


def enrich_with_meta_sidecar(
    result: dict[str, Any],
    text: str,
    *,
    lane: str | None = None,
    enable_meta: bool | None = None,
) -> dict[str, Any]:
    """Attach meta sidecar to an existing compress result when B-track flag is on."""
    use_meta = meta_channel_enabled() if enable_meta is None else bool(enable_meta)
    out = dict(result)
    if not use_meta:
        out["meta_channel"] = None
        out["effective_context_tokens"] = int(out.get("raw_tokens") or 0)
        return out
    sidecar = build_meta_sidecar(
        text,
        lane=lane,
        task_profile="py_coding_dynamic",
        selection_mode="context_scored",
    )
    out["meta_channel"] = sidecar
    raw_tok = int(out.get("raw_tokens") or 0)
    out["effective_context_tokens"] = raw_tok + int(sidecar.get("meta_channel_tokens") or 0)
    out["meta_channel_research_only"] = True
    return out


def coding_proxy_compress_with_meta(
    text: str,
    profile: dict[str, Any],
    *,
    lane: str | None,
    lane_intensity: dict[str, str],
    enable_meta: bool | None = None,
) -> dict[str, Any]:
    """Compress user text; optional meta sidecar when B-track env flag set."""
    from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface

    use_meta = meta_channel_enabled() if enable_meta is None else bool(enable_meta)
    result = dict(
        coding_proxy_compress_surface(text, profile, lane=lane, lane_intensity=lane_intensity)
    )
    result["user_text_only"] = True
    return enrich_with_meta_sidecar(result, text, lane=lane, enable_meta=use_meta)
