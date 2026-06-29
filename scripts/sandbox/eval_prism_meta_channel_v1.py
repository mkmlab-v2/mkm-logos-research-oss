#!/usr/bin/env python3
"""[HYPO] Post-gatekeeper Prism meta channel — pinset sidecar, raw_text-only compress."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _token_in(text: str) -> int:
    from scripts.run_cursor_coding_compress_bench_v1 import _token_in

    return _token_in(text)


def eval_proxy_with_meta_channel(
    raw_text: str,
    pinset_block: str,
    *,
    profile: dict[str, Any],
    lane: str | None,
    lane_intensity: dict[str, str],
    hardening_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate guarded proxy on raw_text; attach pinset via post-gatekeeper meta channel."""
    from scripts.run_cursor_coding_compress_bench_v1 import _eval_proxy_aligned

    if hardening_path is not None:
        os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
        from scripts.core.compression_hardening_v1 import _config_doc

        _config_doc.cache_clear()

    compress = _eval_proxy_aligned(
        raw_text,
        profile,
        lane=lane,
        lane_intensity=lane_intensity,
    )

    from scripts.sandbox.build_prism_pinset_swap_v1 import estimate_pinset_tokens

    meta_tokens = estimate_pinset_tokens(pinset_block)
    raw_tokens = compress.get("raw_tokens")
    if raw_tokens is None:
        raw_tokens = _token_in(raw_text)

    gatekeeper_scope_tokens = _token_in(raw_text)

    return {
        "token_saving_rate": compress.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": compress.get("reconstruction_fidelity_jaccard"),
        "proxy_path": compress.get("proxy_path"),
        "raw_tokens": raw_tokens,
        "compressed_tokens": compress.get("compressed_tokens"),
        "meta_channel": {
            "delivery": "post_gatekeeper_sidecar",
            "attached": bool(pinset_block.strip()),
            "pinset_tokens": meta_tokens,
            "gatekeeper_scope_tokens": gatekeeper_scope_tokens,
            "compress_input_scope": "raw_text_only",
        },
        "total_context_tokens_with_meta": int(raw_tokens) + int(meta_tokens),
    }
