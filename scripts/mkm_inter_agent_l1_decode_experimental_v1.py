#!/usr/bin/env python3
"""Single-shot L1 inverse decoder for v2 expand (research_only · B-track).

Uses the same beam/corpus machinery as ``run_l1_inverse_decoder_spike_test`` but treats
``compressed_text`` as the noisy observation — no ``original_text`` on expand.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Any

from scripts.run_l1_inverse_decoder_spike_test import (
    _apply_literal_channel,
    _beam_candidates,
    _build_corpus,
    _build_position_vocab,
    _cos,
    _encode,
    _extract_literal_channel,
    _repair_tokens_with_vocab,
    _swap_distance_noisy_then_repaired,
)


@lru_cache(maxsize=1)
def _corpus_cached() -> tuple[str, ...]:
    return tuple(_build_corpus())


def decode_compressed_observation_experimental(
    observation: str,
    *,
    beam_size: int = 4,
    seed: int = 701,
    scoring_mode: str = "legacy",
) -> dict[str, Any]:
    """Decode one compressed token string without access to the pre-compress source."""
    noisy = (observation or "").strip()
    if not noisy:
        return {
            "ok": False,
            "error": "empty_observation",
            "decoded_text": "",
            "research_only": True,
        }

    corpus = list(_corpus_cached())
    rng = random.Random(seed)
    src_tokens = noisy.split()
    literal_channel = _extract_literal_channel(src_tokens)
    pos_vocab = _build_position_vocab(corpus)
    observed = _encode(noisy.split())
    noisy_tokens = noisy.split()
    literal_corrupted = any(
        idx < len(noisy_tokens) and ("X" in noisy_tokens[idx] or noisy_tokens[idx] == "OOV_TOKEN")
        for idx in literal_channel.keys()
    )
    cands = _beam_candidates(
        noisy,
        corpus,
        beam_size,
        rng,
        scoring_mode=scoring_mode,
        literal_channel=literal_channel,
        enforce_literal_lock=not literal_corrupted,
        position_vocab=pos_vocab,
    )
    repaired_ref = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
    best = ""
    best_key: tuple[float, ...] | None = None
    for c in cands:
        ct = c.split()
        swap_dist = _swap_distance_noisy_then_repaired(noisy_tokens, repaired_ref, ct)
        cos_s = _cos(observed, _encode(ct))
        key: tuple[float, ...] = (float(swap_dist), -cos_s)
        if best_key is None or key < best_key:
            best_key = key
            best = c
    best_tokens = best.split() if best else noisy_tokens
    restored_tokens = _apply_literal_channel(best_tokens, literal_channel)
    decoded = " ".join(restored_tokens)
    return {
        "ok": True,
        "decoded_text": decoded,
        "beam_size": beam_size,
        "candidate_count": len(cands),
        "research_only": True,
        "decode_path": "l1_inverse_decoder_spike_beam",
        "note": "Batch spike avg exact restore ~58%; per-request decode is not lossless.",
    }
