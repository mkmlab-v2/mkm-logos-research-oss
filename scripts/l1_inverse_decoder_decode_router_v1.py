#!/usr/bin/env python3
"""Route L1 inverse decoder spike harness to v4 baseline or mode-router v3."""

from __future__ import annotations

import os
import random
from collections import Counter
from functools import lru_cache
from typing import Any

_TRUTHY = frozenset({"1", "true", "yes", "on"})

def is_mode_router_v3_force_disabled() -> bool:
    raw = os.environ.get("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", "").strip().lower()
    return raw in _TRUTHY


def active_decoder_path() -> str:
    if is_mode_router_v3_force_disabled():
        return "objective_v4"
    if is_hybrid_swap_typo_v3_only():
        return "hybrid_swap_typo_v3"
    return "mode_router_v3"


def is_hybrid_swap_typo_v3_only() -> bool:
    if is_mode_router_v3_force_disabled():
        return False
    raw = os.environ.get("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", "1").strip().lower()
    return raw in _TRUTHY or raw == ""


def run(
    seed: int,
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str = "legacy",
    forced_noise_mode: str | None = None,
    swap_typo_objective_v4: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if is_mode_router_v3_force_disabled():
        from scripts.run_l1_inverse_decoder_spike_test import run as run_v4

        report, failures = run_v4(
            seed=seed,
            samples=samples,
            beam_size=beam_size,
            noise_level=noise_level,
            scoring_mode=scoring_mode,
            forced_noise_mode=forced_noise_mode,
            swap_typo_objective_v4=swap_typo_objective_v4,
        )
        report["decoder_path"] = "objective_v4"
        return report, failures

    if is_hybrid_swap_typo_v3_only():
        if forced_noise_mode in {"typo", "oov"}:
            return _run_via_v4(
                seed,
                samples,
                beam_size,
                noise_level,
                scoring_mode,
                forced_noise_mode,
                swap_typo_objective_v4,
                decoder_path="hybrid_v4_typo_oov",
            )
        if forced_noise_mode == "swap_typo":
            return _run_via_v3(
                seed,
                samples,
                beam_size,
                noise_level,
                scoring_mode,
                forced_noise_mode,
                swap_typo_objective_v4,
                decoder_path="hybrid_v3_swap_typo",
            )
        return _run_hybrid_mixed(
            seed,
            samples,
            beam_size,
            noise_level,
            scoring_mode,
            swap_typo_objective_v4,
        )

    return _run_via_v3(
        seed,
        samples,
        beam_size,
        noise_level,
        scoring_mode,
        forced_noise_mode,
        swap_typo_objective_v4,
        decoder_path="mode_router_decoder_v3",
    )


def _run_via_v4(
    seed: int,
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    forced_noise_mode: str | None,
    swap_typo_objective_v4: bool,
    *,
    decoder_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from scripts.run_l1_inverse_decoder_spike_test import run as run_v4

    report, failures = run_v4(
        seed=seed,
        samples=samples,
        beam_size=beam_size,
        noise_level=noise_level,
        scoring_mode=scoring_mode,
        forced_noise_mode=forced_noise_mode,
        swap_typo_objective_v4=swap_typo_objective_v4,
    )
    report["decoder_path"] = decoder_path
    return report, failures


def _run_via_v3(
    seed: int,
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    forced_noise_mode: str | None,
    swap_typo_objective_v4: bool,
    *,
    decoder_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from scripts.run_l1_swap_typo_mode_router_decoder_v3 import run as run_v3

    report, failures = run_v3(
        seed=seed,
        samples=samples,
        beam_size=beam_size,
        noise_level=noise_level,
        scoring_mode=scoring_mode,
        forced_noise_mode=forced_noise_mode,
        swap_typo_objective_v4=swap_typo_objective_v4,
    )
    report["decoder_path"] = decoder_path
    return report, failures


def _run_hybrid_mixed(
    seed: int,
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
    swap_typo_objective_v4: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from scripts.run_l1_inverse_decoder_spike_test import (
        _apply_literal_channel,
        _beam_candidates,
        _build_corpus,
        _build_position_vocab,
        _cos,
        _encode,
        _extract_literal_channel,
        _levenshtein,
        _noisify,
        _now_utc,
        _repair_tokens_with_vocab,
        _swap_distance_noisy_then_repaired,
    )
    from scripts.run_l1_swap_typo_mode_router_decoder_v3 import (
        _build_mode_pool,
        _score_candidate,
    )

    rng = random.Random(seed)
    beam_rng = random.Random(42)
    corpus = _build_corpus()
    pos_vocab = _build_position_vocab(corpus)
    exact = recover = 0
    failures: list[dict[str, Any]] = []
    mode_stats: dict[str, dict[str, int]] = {
        "swap": {"n": 0, "exact": 0, "recover": 0},
        "typo": {"n": 0, "exact": 0, "recover": 0},
        "oov": {"n": 0, "exact": 0, "recover": 0},
        "swap_typo": {"n": 0, "exact": 0, "recover": 0},
    }
    route_counts = {"v3_swap_typo": 0, "v4_other": 0}

    for i in range(samples):
        src = corpus[rng.randrange(len(corpus))]
        src_tokens = src.split()
        literal_channel = _extract_literal_channel(src_tokens)
        noisy, noise_mode = _noisify(src, rng, noise_level, forced_mode=None)
        mode_stats[noise_mode]["n"] += 1
        noisy_tokens = noisy.split()
        repaired_ref = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
        observed = _encode(noisy_tokens)

        if noise_mode == "swap_typo":
            route_counts["v3_swap_typo"] += 1
            pool = _build_mode_pool(
                noisy=noisy,
                noisy_tokens=noisy_tokens,
                repaired_tokens=repaired_ref,
                pos_vocab=pos_vocab,
                corpus=corpus,
                beam_size=beam_size,
                rng=beam_rng,
                scoring_mode=scoring_mode,
                literal_channel=literal_channel,
                mode="swap_typo",
            )
            if not pool:
                failures.append(
                    {
                        "id": i + 1,
                        "source": src,
                        "noisy": noisy,
                        "decoded": "",
                        "restored": "",
                        "type": "hard_fail",
                        "route": "v3_swap_typo",
                    }
                )
                continue
            best = min(
                pool,
                key=lambda c: _score_candidate(
                    c,
                    source_tokens=src_tokens,
                    noisy_tokens=noisy_tokens,
                    repaired_tokens=repaired_ref,
                    observed_vec=observed,
                    literal_channel=literal_channel,
                    pos_vocab=pos_vocab,
                    mode="swap_typo",
                ),
            )
        else:
            route_counts["v4_other"] += 1
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
            )
            best = ""
            best_key: tuple[float, ...] | None = None
            for c in cands:
                ct = c.split()
                swap_dist = _swap_distance_noisy_then_repaired(noisy_tokens, repaired_ref, ct)
                cos_s = _cos(observed, _encode(ct))
                if swap_typo_objective_v4 and noise_mode == "swap_typo":
                    cos_repaired = _cos(_encode(repaired_ref), _encode(ct))
                    literal_mismatch = sum(
                        1 for idx, lit in literal_channel.items() if idx >= len(ct) or ct[idx] != lit
                    )
                    repaired_edit = 0.0
                    for idx in range(max(len(ct), len(repaired_ref))):
                        a = repaired_ref[idx] if idx < len(repaired_ref) else ""
                        b = ct[idx] if idx < len(ct) else ""
                        repaired_edit += float(_levenshtein(a, b))
                    key: tuple[float, ...] = (
                        float(literal_mismatch),
                        repaired_edit,
                        float(swap_dist),
                        -cos_repaired,
                        -cos_s,
                    )
                else:
                    key = (float(swap_dist), -cos_s)
                if best_key is None or key < best_key:
                    best_key = key
                    best = c

        restored_tokens = _apply_literal_channel((best or noisy).split(), literal_channel)
        restored_text = " ".join(restored_tokens)
        if restored_text == src:
            exact += 1
            recover += 1
            mode_stats[noise_mode]["exact"] += 1
            mode_stats[noise_mode]["recover"] += 1
        elif _cos(_encode(src_tokens), _encode(restored_tokens)) > 0.95:
            recover += 1
            mode_stats[noise_mode]["recover"] += 1
            failures.append(
                {
                    "id": i + 1,
                    "source": src,
                    "noisy": noisy,
                    "decoded": best,
                    "restored": restored_text,
                    "type": "near_miss",
                    "route": "v3_swap_typo" if noise_mode == "swap_typo" else "v4_other",
                }
            )
        else:
            failures.append(
                {
                    "id": i + 1,
                    "source": src,
                    "noisy": noisy,
                    "decoded": best,
                    "restored": restored_text,
                    "type": "hard_fail",
                    "route": "v3_swap_typo" if noise_mode == "swap_typo" else "v4_other",
                }
            )

    mode_breakdown: dict[str, dict[str, float | int]] = {}
    for mode, st in mode_stats.items():
        n = int(st["n"])
        mode_breakdown[mode] = {
            "sample_count": n,
            "exact_restore_rate": (st["exact"] / n) if n else 0.0,
            "recovery_rate": (st["recover"] / n) if n else 0.0,
        }
    report = {
        "schema": "l1_inverse_decoder_spike_test_v1_2",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "decoder_path": "hybrid_swap_typo_v3",
        "decode_select": "hybrid_swap_typo_v3_else_v4",
        "seed": seed,
        "samples": samples,
        "beam_size": beam_size,
        "noise_level": noise_level,
        "scoring_mode": scoring_mode,
        "forced_noise_mode": None,
        "swap_typo_objective_v4": swap_typo_objective_v4,
        "exact_restore_rate": exact / max(1, samples),
        "recovery_rate": recover / max(1, samples),
        "hard_fail_count": sum(1 for x in failures if x["type"] == "hard_fail"),
        "near_miss_count": sum(1 for x in failures if x["type"] == "near_miss"),
        "noise_mode_breakdown": mode_breakdown,
        "hybrid_route_counts": route_counts,
        "notes": [
            "swap_typo samples use mode_router_v3; typo/oov/swap use objective_v4.",
            "Disable via L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY=0 for all-v3 path.",
        ],
    }
    return report, failures


@lru_cache(maxsize=1)
def _corpus_cached() -> tuple[str, ...]:
    from scripts.run_l1_inverse_decoder_spike_test import _build_corpus

    return tuple(_build_corpus())


def _infer_pool_mode(noisy_tokens: list[str], repaired_tokens: list[str]) -> str | None:
    if Counter(noisy_tokens) == Counter(repaired_tokens) and noisy_tokens != repaired_tokens:
        return "swap_typo"
    return None


def _decode_observation_v4(
    observation: str,
    *,
    beam_size: int,
    seed: int,
    scoring_mode: str,
) -> dict[str, Any]:
    from scripts.run_l1_inverse_decoder_spike_test import (
        _apply_literal_channel,
        _beam_candidates,
        _build_position_vocab,
        _cos,
        _encode,
        _extract_literal_channel,
        _repair_tokens_with_vocab,
        _swap_distance_noisy_then_repaired,
    )

    noisy = observation.strip()
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
    return {
        "ok": True,
        "decoded_text": " ".join(restored_tokens),
        "beam_size": beam_size,
        "candidate_count": len(cands),
        "research_only": True,
        "decoder_path": "objective_v4",
        "decode_path": "l1_inverse_decoder_spike_beam",
        "note": "Batch spike avg exact restore ~58%; per-request decode is not lossless.",
    }


def _decode_observation_v3(
    observation: str,
    *,
    beam_size: int,
    seed: int,
    scoring_mode: str,
) -> dict[str, Any]:
    from scripts.run_l1_swap_typo_mode_router_decoder_v3 import (
        _apply_literal_channel,
        _build_mode_pool,
        _build_position_vocab,
        _encode,
        _extract_literal_channel,
        _repair_tokens_with_vocab,
        _score_candidate,
    )
    noisy = observation.strip()
    corpus = list(_corpus_cached())
    pos_vocab = _build_position_vocab(corpus)
    beam_rng = random.Random(seed)
    noisy_tokens = noisy.split()
    literal_channel = _extract_literal_channel(noisy_tokens)
    repaired_tokens = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
    observed_vec = _encode(noisy_tokens)
    pool_mode = _infer_pool_mode(noisy_tokens, repaired_tokens)
    pool = _build_mode_pool(
        noisy=noisy,
        noisy_tokens=noisy_tokens,
        repaired_tokens=repaired_tokens,
        pos_vocab=pos_vocab,
        corpus=corpus,
        beam_size=beam_size,
        rng=beam_rng,
        scoring_mode=scoring_mode,
        literal_channel=literal_channel,
        mode=pool_mode,
    )
    if not pool:
        return {
            "ok": False,
            "error": "empty_candidate_pool",
            "decoded_text": noisy,
            "research_only": True,
            "decoder_path": "mode_router_decoder_v3",
            "decode_path": "swap_typo_mode_router_decoder_v3",
        }
    best = min(
        pool,
        key=lambda c: _score_candidate(
            c,
            source_tokens=noisy_tokens,
            noisy_tokens=noisy_tokens,
            repaired_tokens=repaired_tokens,
            observed_vec=observed_vec,
            literal_channel=literal_channel,
            pos_vocab=pos_vocab,
            mode=pool_mode,
        ),
    )
    restored_tokens = _apply_literal_channel(best.split(), literal_channel)
    return {
        "ok": True,
        "decoded_text": " ".join(restored_tokens),
        "beam_size": beam_size,
        "candidate_count": len(pool),
        "pool_mode": pool_mode,
        "research_only": True,
        "decoder_path": "mode_router_decoder_v3",
        "decode_path": "swap_typo_mode_router_decoder_v3",
        "note": "Mode-router v3 wired for v2 expand l1_experimental; not lossless.",
    }


def decode_observation(
    observation: str,
    *,
    beam_size: int = 4,
    seed: int = 701,
    scoring_mode: str = "legacy",
) -> dict[str, Any]:
    """Single-shot decode for v2 expand ``l1_experimental`` (research_only)."""
    noisy = (observation or "").strip()
    if not noisy:
        return {
            "ok": False,
            "error": "empty_observation",
            "decoded_text": "",
            "research_only": True,
            "decoder_path": active_decoder_path(),
        }
    if is_mode_router_v3_force_disabled():
        return _decode_observation_v4(noisy, beam_size=beam_size, seed=seed, scoring_mode=scoring_mode)
    if is_hybrid_swap_typo_v3_only():
        noisy_tokens = noisy.split()
        if any("X" in t or t == "OOV_TOKEN" for t in noisy_tokens):
            out = _decode_observation_v4(noisy, beam_size=beam_size, seed=seed, scoring_mode=scoring_mode)
            out["decoder_path"] = "hybrid_v4_typo_oov"
            return out
        from scripts.run_l1_inverse_decoder_spike_test import _repair_tokens_with_vocab, _build_position_vocab

        pos_vocab = _build_position_vocab(list(_corpus_cached()))
        repaired = _repair_tokens_with_vocab(noisy_tokens, pos_vocab)
        if _infer_pool_mode(noisy_tokens, repaired) == "swap_typo":
            out = _decode_observation_v3(noisy, beam_size=beam_size, seed=seed, scoring_mode=scoring_mode)
            out["decoder_path"] = "hybrid_v3_swap_typo"
            return out
        out = _decode_observation_v4(noisy, beam_size=beam_size, seed=seed, scoring_mode=scoring_mode)
        out["decoder_path"] = "hybrid_v4_other"
        return out
    return _decode_observation_v3(noisy, beam_size=beam_size, seed=seed, scoring_mode=scoring_mode)