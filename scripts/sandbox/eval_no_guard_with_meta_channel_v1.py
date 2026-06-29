#!/usr/bin/env python3
"""[HYPO] No-Guard eval with Prism attachment modes (B-track sandbox)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]

InjectionMode = Literal["none", "prepend", "meta_channel_post_gatekeeper"]


def _apply_no_guard(profile_path: Path) -> dict[str, str]:
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(profile_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    doc = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    block = doc.get("lane_intensity")
    return block if isinstance(block, dict) else {}


def eval_no_guard_with_attachment(
    text: str,
    *,
    no_guard_profile: Path,
    lane: str | None,
    attachment_block: str = "",
    injection_mode: InjectionMode = "none",
    must_keep_extra: set[str] | None = None,
) -> dict[str, Any]:
    """No-Guard: always compress user path; pinset optional via prepend or meta sidecar."""
    from scripts.sandbox.build_prism_pinset_swap_v1 import estimate_pinset_tokens
    from scripts.sandbox.run_no_guard_limit_stress_test_v1 import _eval_no_guard, _token_in

    lane_intensity = _apply_no_guard(no_guard_profile)
    mode = injection_mode or "none"
    block = attachment_block or ""
    meta_tokens = estimate_pinset_tokens(block) if block else 0
    extra = must_keep_extra or set()

    compress_text = (block + text) if mode == "prepend" and block else text
    metrics = _eval_no_guard(
        compress_text,
        lane=lane,
        lane_intensity=lane_intensity,
        must_keep_extra=extra,
    )
    user_tokens = _token_in(text)
    compress_input_tokens = _token_in(compress_text)

    metrics["injection_mode"] = mode
    metrics["user_text_tokens"] = user_tokens
    metrics["compress_input_tokens"] = compress_input_tokens
    metrics["no_guard_profile"] = str(no_guard_profile.relative_to(ROOT)).replace("\\", "/")

    if mode == "meta_channel_post_gatekeeper" and block:
        metrics["meta_channel_tokens"] = meta_tokens
        metrics["meta_channel_present"] = True
        raw_tok = int(metrics.get("raw_tokens") or metrics.get("input_tokens") or user_tokens)
        metrics["effective_context_tokens"] = raw_tok + meta_tokens
        metrics["user_fidelity_scope"] = "compress_input_is_user_text_only"
    else:
        metrics["meta_channel_tokens"] = meta_tokens if mode == "prepend" and block else 0
        metrics["meta_channel_present"] = False
        metrics["effective_context_tokens"] = int(
            metrics.get("raw_tokens") or metrics.get("input_tokens") or compress_input_tokens
        )
        metrics["user_fidelity_scope"] = "full_compress_input"

    return metrics
