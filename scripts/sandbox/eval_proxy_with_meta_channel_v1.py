#!/usr/bin/env python3
"""[HYPO] Coding proxy eval with Prism attachment modes (B-track sandbox)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]

InjectionMode = Literal["none", "prepend", "meta_channel_post_gatekeeper"]


def _prepare_hardening(hardening_path: Path) -> None:
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()


def eval_proxy_with_attachment(
    text: str,
    profile: dict[str, Any],
    *,
    lane: str | None,
    lane_intensity: dict[str, str],
    attachment_block: str = "",
    injection_mode: InjectionMode = "none",
) -> dict[str, Any]:
    """Evaluate compression proxy; optional pinset via prepend or post-gatekeeper meta channel."""
    from scripts.run_cursor_coding_compress_bench_v1 import _eval_proxy_aligned, _token_in
    from scripts.sandbox.build_prism_pinset_swap_v1 import estimate_pinset_tokens

    mode = injection_mode or "none"
    block = attachment_block or ""
    meta_tokens = estimate_pinset_tokens(block) if block else 0

    if mode == "prepend" and block:
        metrics = _eval_proxy_aligned(
            block + text,
            profile,
            lane=lane,
            lane_intensity=lane_intensity,
        )
        metrics["injection_mode"] = mode
        metrics["meta_channel_tokens"] = meta_tokens
        metrics["user_text_tokens"] = _token_in(text)
        metrics["gatekeeper_input_tokens"] = _token_in(block + text)
        return metrics

    metrics = _eval_proxy_aligned(text, profile, lane=lane, lane_intensity=lane_intensity)
    metrics["injection_mode"] = mode
    metrics["user_text_tokens"] = _token_in(text)
    metrics["gatekeeper_input_tokens"] = _token_in(text)

    if mode == "meta_channel_post_gatekeeper" and block:
        raw_tok = int(metrics.get("raw_tokens") or metrics.get("user_text_tokens") or 0)
        metrics["meta_channel_tokens"] = meta_tokens
        metrics["meta_channel_present"] = True
        metrics["effective_context_tokens"] = raw_tok + meta_tokens
    else:
        metrics["meta_channel_tokens"] = 0
        metrics["meta_channel_present"] = False
        metrics["effective_context_tokens"] = int(
            metrics.get("raw_tokens") or metrics.get("user_text_tokens") or 0
        )

    return metrics


def load_guarded_context(hardening_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    from scripts.run_cursor_coding_compress_bench_v1 import _load_lane_intensity, _selected_profile

    _prepare_hardening(hardening_path)
    return _selected_profile(), _load_lane_intensity(hardening_path)
