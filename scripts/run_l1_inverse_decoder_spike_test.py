#!/usr/bin/env python3
"""Day 6-8 L1 inverse decoder spike: constrained beam + noise injection."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_latest.json"
DEFAULT_FAIL = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_failures_latest.jsonl"
DEFAULT_SWEEP_OUT = ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_spike_test_summary_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize(q: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(q))
    if n == 0.0:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / n


def _qmul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        dtype=np.float64,
    )


def _token_quat(token: str) -> np.ndarray:
    h = hashlib.sha256(token.encode("utf-8")).digest()
    vals = [int.from_bytes(h[i : i + 8], "big", signed=False) for i in range(0, 32, 8)]
    q = np.array([(v % 1000003) / 1000003.0 for v in vals], dtype=np.float64)
    q = (q * 2.0) - 1.0
    return _normalize(q)


def _encode(tokens: list[str]) -> np.ndarray:
    q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for t in tokens:
        q = _qmul(q, _token_quat(t))
    return _normalize(q)


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _inversion_count_naive(idxs: list[int]) -> int:
    n = len(idxs)
    inv = 0
    for i in range(n):
        for j in range(i + 1, n):
            if idxs[i] > idxs[j]:
                inv += 1
    return inv


def _min_adjacent_swaps_same_multiset(source: list[str], target: list[str]) -> int | None:
    """Minimum adjacent swaps to turn `source` into `target` (same multiset); else None."""
    if len(source) != len(target):
        return None
    if Counter(source) != Counter(target):
        return None
    occ: dict[str, deque[int]] = defaultdict(deque)
    for i, tok in enumerate(source):
        occ[tok].append(i)
    pulled: list[int] = []
    for tok in target:
        q = occ.get(tok)
        if not q:
            return None
        pulled.append(q.popleft())
    return _inversion_count_naive(pulled)


def _swap_distance_noisy_then_repaired(noisy: list[str], repaired: list[str], cand: list[str]) -> int:
    """Prefer swap distance vs raw observation; if multiset mismatch (typo/OOV), use repaired ref."""
    d = _min_adjacent_swaps_same_multiset(noisy, cand)
    if d is not None:
        return d
    d2 = _min_adjacent_swaps_same_multiset(repaired, cand)
    if d2 is not None:
        return d2
    return 10**9


def _swap_fit_score(noisy: list[str], repaired: list[str], cand: list[str]) -> float:
    """[0,1]: 1 = zero adjacent swaps vs ref (noisy or repaired fallback)."""
    d = _swap_distance_noisy_then_repaired(noisy, repaired, cand)
    if d >= 10**9:
        return 0.0
    n = len(cand)
    cap = max(1, n * (n - 1) // 2)
    return 1.0 - min(d, cap) / cap


def _build_corpus() -> list[str]:
    subjects = ["내가", "그가", "우리가", "팀이", "시스템이"]
    objects = ["사과를", "모델을", "문서를", "데이터를", "리포트를", "신호를"]
    verbs = ["먹었다", "분석했다", "요약했다", "검증했다", "생성했다", "정렬했다"]
    adverbs = ["오늘", "방금", "정밀하게", "신속히"]
    qualifiers = ["정상으로", "보수적으로", "안전하게", "연구모드로"]
    out: list[str] = []
    literals = ["ID_A12", "BTCUSDT", "2026-04-09", "P0"]
    for adv in adverbs:
        for s in subjects:
            for o in objects:
                for q in qualifiers:
                    for v in verbs:
                        for lit in literals:
                            out.append(f"{adv} {s} {lit} {o} {q} {v}")
    # deterministic unique ordering
    return sorted(set(out))


def _token_hamming_like(a: str, b: str) -> int:
    if len(a) != len(b):
        return abs(len(a) - len(b)) + 10
    return sum(1 for x, y in zip(a, b) if x != y)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def _build_position_vocab(corpus: list[str]) -> dict[int, set[str]]:
    pos_vocab: dict[int, set[str]] = defaultdict(set)
    for sent in corpus:
        toks = sent.split()
        for i, tok in enumerate(toks):
            pos_vocab[i].add(tok)
    return dict(pos_vocab)


def _repair_tokens_with_vocab(noisy_tokens: list[str], pos_vocab: dict[int, set[str]]) -> list[str]:
    repaired = noisy_tokens[:]
    for i, tok in enumerate(repaired):
        vocab = pos_vocab.get(i, set())
        if not vocab:
            continue
        # OOV placeholder fallback: use lexically nearest candidate for the position.
        if tok == "OOV_TOKEN":
            repaired[i] = min(vocab, key=lambda v: (_levenshtein(v, "OOVTOKEN"), _token_hamming_like(v, "OOVTOKEN")))
            continue
        if "X" in tok:
            nearest = min(vocab, key=lambda v: (_levenshtein(v, tok), _token_hamming_like(v, tok)))
            if _levenshtein(nearest, tok) <= 2:
                repaired[i] = nearest
            else:
                # Fallback: treat X as wildcard and prefer same-length vocab matches.
                same_len = [v for v in vocab if len(v) == len(tok)]
                if same_len:
                    repaired[i] = min(same_len, key=lambda v: _token_hamming_like(v, tok))
        elif tok not in vocab:
            # Unknown token fallback using edit distance to position vocabulary.
            nearest = min(vocab, key=lambda v: (_levenshtein(v, tok), _token_hamming_like(v, tok)))
            if _levenshtein(nearest, tok) <= 1:
                repaired[i] = nearest
    return repaired


def _position_token_fit_score(tok: str, pos_vocab_set: set[str]) -> float:
    if not pos_vocab_set:
        return -10.0
    if tok in pos_vocab_set:
        return 3.0
    nearest = min(pos_vocab_set, key=lambda v: (_levenshtein(v, tok), _token_hamming_like(v, tok)))
    lev = _levenshtein(nearest, tok)
    ham = _token_hamming_like(nearest, tok)
    return -float(lev) - (0.1 * float(ham))


def _position_constrained_reorder(tokens: list[str], pos_vocab: dict[int, set[str]]) -> list[str]:
    n = len(tokens)
    if n <= 1:
        return tokens[:]
    idxs = list(range(n))
    # Greedy assignment keeps runtime bounded in long sweeps.
    remaining = set(idxs)
    best_perm: list[int] = []
    for pos in range(n):
        best_idx = max(
            remaining,
            key=lambda src_idx: _position_token_fit_score(tokens[src_idx], pos_vocab.get(pos, set())),
        )
        best_perm.append(best_idx)
        remaining.remove(best_idx)
    return [tokens[i] for i in best_perm]


def _generate_adjacent_transposition_candidates(tokens: list[str], max_steps: int = 3) -> set[str]:
    if len(tokens) <= 1:
        return {" ".join(tokens)}
    seen: set[tuple[str, ...]] = {tuple(tokens)}
    frontier: set[tuple[str, ...]] = {tuple(tokens)}
    for _ in range(max_steps):
        next_frontier: set[tuple[str, ...]] = set()
        for seq in frontier:
            seq_list = list(seq)
            for i in range(len(seq_list) - 1):
                cand = seq_list[:]
                cand[i], cand[i + 1] = cand[i + 1], cand[i]
                t = tuple(cand)
                if t not in seen:
                    seen.add(t)
                    next_frontier.add(t)
        if not next_frontier:
            break
        frontier = next_frontier
    return {" ".join(x) for x in seen}


def _is_literal_token(tok: str) -> bool:
    return any(ch.isdigit() for ch in tok) or "_" in tok or "-" in tok or tok.isupper()


def _extract_literal_channel(tokens: list[str]) -> dict[int, str]:
    return {i: tok for i, tok in enumerate(tokens) if _is_literal_token(tok)}


def _apply_literal_channel(decoded_tokens: list[str], literal_channel: dict[int, str]) -> list[str]:
    out = decoded_tokens[:]
    for idx, literal in literal_channel.items():
        if idx < len(out):
            out[idx] = literal
    return out


def _noisify(sentence: str, rng: random.Random, noise_level: float, forced_mode: str | None = None) -> tuple[str, str]:
    toks = sentence.split()
    mode = forced_mode or rng.choice(["swap", "typo", "oov", "swap_typo"])
    if mode in {"swap", "swap_typo"} and len(toks) >= 2:
        swap_count = 2 if noise_level >= 0.2 else 1
        for _ in range(swap_count):
            i, j = rng.randrange(len(toks)), rng.randrange(len(toks))
            toks[i], toks[j] = toks[j], toks[i]
    literal_positions = [i for i, t in enumerate(toks) if _is_literal_token(t)]
    if mode in {"typo", "swap_typo"}:
        typo_count = 2 if noise_level >= 0.2 else 1
        for _ in range(typo_count):
            idx = rng.choice(literal_positions) if literal_positions else rng.randrange(len(toks))
            t = toks[idx]
            if len(t) >= 2:
                pos = rng.randrange(len(t))
                chars = list(t)
                chars[pos] = "X"
                toks[idx] = "".join(chars)
    if mode == "oov":
        oov_count = 2 if noise_level >= 0.2 else 1
        for _ in range(oov_count):
            idx = rng.choice(literal_positions) if literal_positions else rng.randrange(len(toks))
            toks[idx] = "OOV_TOKEN"
    return " ".join(toks), mode


def _beam_candidates(
    noisy: str,
    corpus: list[str],
    beam_size: int,
    rng: random.Random,
    scoring_mode: str = "legacy",
    literal_channel: dict[int, str] | None = None,
    enforce_literal_lock: bool = True,
    *,
    position_vocab: dict[int, set[str]] | None = None,
) -> list[str]:
    toks = noisy.split()
    pos_vocab = position_vocab if position_vocab is not None else _build_position_vocab(corpus)
    repaired = _repair_tokens_with_vocab(toks, pos_vocab)
    multiset_dirty = Counter(toks) != Counter(repaired)
    typo_or_oov_obs = any("X" in t or t == "OOV_TOKEN" for t in toks)
    swap_typo_like = multiset_dirty and typo_or_oov_obs

    pool = set(corpus)
    # Add repaired sentence candidate (position-aware typo/OOV correction).
    pool.add(" ".join(repaired))
    # Swap-focused candidate: position-constrained reordering from observed/repaired tokens.
    pool.add(" ".join(_position_constrained_reorder(toks, pos_vocab)))
    pool.add(" ".join(_position_constrained_reorder(repaired, pos_vocab)))
    # Swap-focused candidate family: bounded adjacent transposition paths.
    pool.update(_generate_adjacent_transposition_candidates(toks, max_steps=3))
    pool.update(_generate_adjacent_transposition_candidates(repaired, max_steps=3))
    # Constrained local permutations of observed noisy sequence.
    if len(toks) <= 6:
        for p in itertools.permutations(toks):
            pool.add(" ".join(p))
        # Also permute repaired tokens for stronger typo recovery under swaps.
        for p in itertools.permutations(repaired):
            pool.add(" ".join(p))
    else:
        for _ in range(64):
            c = toks[:]
            i, j = rng.randrange(len(c)), rng.randrange(len(c))
            c[i], c[j] = c[j], c[i]
            pool.add(" ".join(c))
    # If literal lock is active, prioritize candidates that keep literal anchors fixed.
    if enforce_literal_lock and literal_channel:
        locked_pool = {
            sent
            for sent in pool
            if all((idx < len(sent.split()) and sent.split()[idx] == lit) for idx, lit in literal_channel.items())
        }
        if locked_pool:
            pool = locked_pool
    # Keep deterministic top beam_size * 12 by selected scoring mode.
    scored = []
    noisy_set = set(toks)
    repaired_set = set(repaired)

    noisy_pos = {tok: idx for idx, tok in enumerate(toks)}
    noisy_bigrams = set(zip(toks, toks[1:])) if len(toks) >= 2 else set()
    literal_channel = literal_channel or {}
    noisy_literals_in_order = [tok for _, tok in sorted(literal_channel.items())]

    def _order_consistency_score(st: list[str]) -> float:
        # Penalize candidates that preserve token set but scramble order.
        common = [tok for tok in st if tok in noisy_pos]
        if not common:
            return 0.0
        dist = 0.0
        for i, tok in enumerate(st):
            if tok in noisy_pos:
                dist += abs(i - noisy_pos[tok])
        # convert to [0,1] where 1 is best order consistency
        return 1.0 - (dist / max(1.0, len(st) * len(st)))

    def _bigram_consistency_score(st: list[str]) -> float:
        if len(st) < 2 or not noisy_bigrams:
            return 0.0
        cand_bigrams = set(zip(st, st[1:]))
        return len(cand_bigrams & noisy_bigrams) / max(1, len(noisy_bigrams))

    def _literal_relative_order_penalty(st: list[str]) -> float:
        if len(noisy_literals_in_order) <= 1:
            return 0.0
        cand_pos: dict[str, int] = {}
        for i, tok in enumerate(st):
            if tok in noisy_literals_in_order and tok not in cand_pos:
                cand_pos[tok] = i
        inversions = 0
        pairs = 0
        for i in range(len(noisy_literals_in_order)):
            for j in range(i + 1, len(noisy_literals_in_order)):
                a = noisy_literals_in_order[i]
                b = noisy_literals_in_order[j]
                if a in cand_pos and b in cand_pos:
                    pairs += 1
                    if cand_pos[a] > cand_pos[b]:
                        inversions += 1
        return (inversions / pairs) if pairs else 0.0

    # Pure swap: multiset matches repaired; rely on final min-swap selection, not beam duplication.
    # Typo/OOV + multiset drift: push swap_fit harder in beam ordering.
    beam_swap_w_legacy = 0.24 if swap_typo_like else (0.14 if multiset_dirty else 0.0)
    beam_swap_w_enh = 0.22 if swap_typo_like else (0.12 if multiset_dirty else 0.0)
    beam_swap_w_v2 = 0.40 if swap_typo_like else (0.28 if multiset_dirty else 0.10)

    for sent in pool:
        st = sent.split()
        st_set = set(st)
        jac_noisy = len(noisy_set & st_set) / max(1, len(noisy_set | st_set))
        jac_repaired = len(repaired_set & st_set) / max(1, len(repaired_set | st_set))
        position_hits = sum(1 for idx, tok in enumerate(st) if idx < len(repaired) and tok == repaired[idx])
        order_score = _order_consistency_score(st)
        bigram_score = _bigram_consistency_score(st)
        literal_order_penalty = _literal_relative_order_penalty(st)
        swap_fit = _swap_fit_score(toks, repaired, st)
        literal_lock_score = 0.0
        literal_mismatch_penalty = 0.0
        if enforce_literal_lock and literal_channel:
            literal_lock_hits = sum(
                1
                for idx, lit in literal_channel.items()
                if idx < len(st) and st[idx] == lit
            )
            literal_lock_score = literal_lock_hits / max(1, len(literal_channel))
            # Penalize candidates that move literal anchors away from source positions.
            mismatches = sum(
                1 for idx, lit in literal_channel.items() if idx >= len(st) or st[idx] != lit
            )
            literal_mismatch_penalty = mismatches / len(literal_channel)
        if scoring_mode == "legacy":
            score = (
                0.55 * jac_noisy
                + 0.35 * jac_repaired
                + 0.05 * (position_hits / max(1, len(toks)))
                + beam_swap_w_legacy * swap_fit
                + 0.25 * literal_lock_score
                - 0.20 * literal_mismatch_penalty
                + (0.15 if len(st) == len(toks) else 0.0)
            )
        elif scoring_mode == "swap_v2":
            if swap_typo_like:
                # Noisy bigrams/order are unreliable with X/OOV; lean on repaired + swap_fit.
                score = (
                    0.16 * jac_noisy
                    + 0.16 * jac_repaired
                    + 0.24 * (position_hits / max(1, len(toks)))
                    + 0.14 * order_score
                    + 0.20 * bigram_score
                    + beam_swap_w_v2 * swap_fit
                    + 0.22 * literal_lock_score
                    - 0.18 * literal_mismatch_penalty
                    - 0.25 * literal_order_penalty
                    + (0.15 if len(st) == len(toks) else 0.0)
                )
            else:
                score = (
                    0.20 * jac_noisy
                    + 0.10 * jac_repaired
                    + 0.20 * (position_hits / max(1, len(toks)))
                    + 0.30 * order_score
                    + 0.40 * bigram_score
                    + beam_swap_w_v2 * swap_fit
                    + 0.20 * literal_lock_score
                    - 0.20 * literal_mismatch_penalty
                    - 0.35 * literal_order_penalty
                    + (0.15 if len(st) == len(toks) else 0.0)
                )
        else:
            score = (
                0.45 * jac_noisy
                + 0.30 * jac_repaired
                + 0.15 * (position_hits / max(1, len(toks)))
                + 0.10 * order_score
                + beam_swap_w_enh * swap_fit
                + 0.25 * literal_lock_score
                - 0.20 * literal_mismatch_penalty
                + (0.15 if len(st) == len(toks) else 0.0)
            )
        scored.append((score, sent))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[: max(beam_size * 12, 12)]]


def run(
    seed: int,
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str = "legacy",
    forced_noise_mode: str | None = None,
    swap_typo_objective_v4: bool = True,
) -> tuple[dict, list[dict]]:
    rng = random.Random(seed)
    corpus = _build_corpus()
    exact = 0
    recover = 0
    failures: list[dict] = []
    mode_stats = {
        "swap": {"n": 0, "exact": 0, "recover": 0},
        "typo": {"n": 0, "exact": 0, "recover": 0},
        "oov": {"n": 0, "exact": 0, "recover": 0},
        "swap_typo": {"n": 0, "exact": 0, "recover": 0},
    }
    for i in range(samples):
        src = corpus[rng.randrange(len(corpus))]
        src_tokens = src.split()
        literal_channel = _extract_literal_channel(src_tokens)
        noisy, noise_mode = _noisify(src, rng, noise_level, forced_mode=forced_noise_mode)
        mode_stats[noise_mode]["n"] += 1
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
        )
        pos_vocab_run = _build_position_vocab(corpus)
        repaired_ref = _repair_tokens_with_vocab(noisy_tokens, pos_vocab_run)
        best = ""
        best_key: tuple[int, float] | None = None
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
                # v4: literal anchors + repaired positional edit drive selection.
                key = (float(literal_mismatch), repaired_edit, float(swap_dist), -cos_repaired, -cos_s)
            else:
                # Primary: fewer adjacent swaps vs observation; tie-break: higher cosine to observed embedding.
                key = (swap_dist, -cos_s)
            if best_key is None or key < best_key:
                best_key = key
                best = c
        best_tokens = best.split()
        restored_tokens = _apply_literal_channel(best_tokens, literal_channel)
        restored_text = " ".join(restored_tokens)
        if restored_text == src:
            exact += 1
            recover += 1
            mode_stats[noise_mode]["exact"] += 1
            mode_stats[noise_mode]["recover"] += 1
        elif _cos(_encode(src.split()), _encode(restored_tokens)) > 0.95:
            recover += 1
            mode_stats[noise_mode]["recover"] += 1
            failures.append({"id": i + 1, "source": src, "noisy": noisy, "decoded": best, "restored": restored_text, "type": "near_miss"})
        else:
            failures.append({"id": i + 1, "source": src, "noisy": noisy, "decoded": best, "restored": restored_text, "type": "hard_fail"})

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
        "decode_target": "noisy_observation",
        "decode_select": (
            "swap_typo_objective_v4_literal_and_repaired_edit_priority"
            if swap_typo_objective_v4
            else "min_adjacent_swap_noisy_then_repaired_then_cosine"
        ),
        "seed": seed,
        "samples": samples,
        "beam_size": beam_size,
        "noise_level": noise_level,
        "scoring_mode": scoring_mode,
        "forced_noise_mode": forced_noise_mode,
        "swap_typo_objective_v4": swap_typo_objective_v4,
        "exact_restore_rate": exact / max(1, samples),
        "recovery_rate": recover / max(1, samples),
        "hard_fail_count": sum(1 for x in failures if x["type"] == "hard_fail"),
        "near_miss_count": sum(1 for x in failures if x["type"] == "near_miss"),
        "noise_mode_breakdown": mode_breakdown,
        "notes": [
            "Spike harness for constrained candidate beam + noise injection.",
            "Not a production certificate; use with fixed-seed rerun checks.",
            "Default scoring_mode=legacy: harness SSOT baseline for regression artifacts; swap_v2 is research-only.",
            "Canary default: swap_typo objective v4 enabled unless explicitly disabled.",
        ],
    }
    return report, failures


def run_sweep(seeds: list[int], noise_levels: list[float], samples: int, beam_size: int, scoring_mode: str) -> dict:
    cells: list[dict] = []
    per_seed_best: dict[int, float] = {}
    for seed in seeds:
        per_seed_best[seed] = 0.0
        for nl in noise_levels:
            rep, _ = run(
                seed=seed,
                samples=samples,
                beam_size=beam_size,
                noise_level=nl,
                scoring_mode=scoring_mode,
            )
            exact_rate = float(rep["exact_restore_rate"])
            cells.append(
                {
                    "seed": seed,
                    "noise_level": nl,
                    "exact_restore_rate": exact_rate,
                    "recovery_rate": float(rep["recovery_rate"]),
                    "hard_fail_count": int(rep["hard_fail_count"]),
                }
            )
            if exact_rate > per_seed_best[seed]:
                per_seed_best[seed] = exact_rate

    exact_vals = [c["exact_restore_rate"] for c in cells]
    recovery_vals = [c["recovery_rate"] for c in cells]
    per_seed_avg = []
    for seed in seeds:
        seed_cells = [c for c in cells if c["seed"] == seed]
        avg_exact = sum(c["exact_restore_rate"] for c in seed_cells) / max(1, len(seed_cells))
        per_seed_avg.append(avg_exact)

    determinism_delta = max(per_seed_avg) - min(per_seed_avg) if per_seed_avg else None
    return {
        "schema": "l1_inverse_decoder_spike_test_summary_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "seeds": seeds,
        "noise_levels": noise_levels,
        "samples_per_cell": samples,
        "beam_size": beam_size,
        "scoring_mode": scoring_mode,
        "aggregate": {
            "min_exact_restore_rate": min(exact_vals) if exact_vals else None,
            "max_exact_restore_rate": max(exact_vals) if exact_vals else None,
            "avg_exact_restore_rate": (sum(exact_vals) / len(exact_vals)) if exact_vals else None,
            "min_recovery_rate": min(recovery_vals) if recovery_vals else None,
            "avg_recovery_rate": (sum(recovery_vals) / len(recovery_vals)) if recovery_vals else None,
            "determinism_delta": determinism_delta,
        },
        "cells": cells,
        "notes": [
            "Determinism delta is spread of per-seed average exact_restore_rate.",
            "Use fixed seeds and fixed corpus for reproducibility comparisons.",
        ],
    }


def run_noise_mode_breakdown(
    seeds: list[int],
    samples: int,
    beam_size: int,
    noise_level: float,
    scoring_mode: str,
) -> dict:
    modes = ["swap", "typo", "oov", "swap_typo"]
    rows: list[dict] = []
    for mode in modes:
        exact_vals: list[float] = []
        recovery_vals: list[float] = []
        for seed in seeds:
            rep, _ = run(
                seed=seed,
                samples=samples,
                beam_size=beam_size,
                noise_level=noise_level,
                scoring_mode=scoring_mode,
                forced_noise_mode=mode,
            )
            exact_vals.append(float(rep["exact_restore_rate"]))
            recovery_vals.append(float(rep["recovery_rate"]))
        rows.append(
            {
                "mode": mode,
                "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
                "min_exact_restore_rate": min(exact_vals),
                "max_exact_restore_rate": max(exact_vals),
                "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
            }
        )
    rows.sort(key=lambda x: float(x["avg_exact_restore_rate"]))
    return {
        "schema": "l1_inverse_decoder_noise_mode_breakdown_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples_per_seed": samples,
            "beam_size": beam_size,
            "noise_level": noise_level,
            "scoring_mode": scoring_mode,
        },
        "hardest_mode": rows[0] if rows else None,
        "easiest_mode": rows[-1] if rows else None,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=701)
    ap.add_argument("--samples", type=int, default=180)
    ap.add_argument("--beam-size", type=int, default=4)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--sweep", action="store_true", help="Run multi-seed/noise sweep and write summary artifact.")
    ap.add_argument("--seeds", type=str, default="701,809,907")
    ap.add_argument("--noise-levels", type=str, default="0.1,0.2")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fail-log", type=Path, default=DEFAULT_FAIL)
    ap.add_argument("--sweep-out", type=Path, default=DEFAULT_SWEEP_OUT)
    ap.add_argument(
        "--scoring-mode",
        choices=("legacy", "enhanced", "swap_v2"),
        default="legacy",
        help=(
            "Beam pre-rank scorer: legacy=SSOT baseline (default); enhanced=order-aware B; "
            "swap_v2=research-only swap/bigram mix (not default for regression)."
        ),
    )
    ap.add_argument(
        "--noise-breakdown",
        action="store_true",
        help="Generate mode-wise breakdown (swap/typo/oov/swap_typo).",
    )
    ap.add_argument(
        "--noise-breakdown-out",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "l1_inverse_decoder_noise_mode_breakdown_latest.json",
    )
    ap.add_argument(
        "--forced-noise-mode",
        default=None,
        choices=("swap", "typo", "oov", "swap_typo"),
        help=(
            "Fix noise injection to one mode for the single run (default: mixed). "
            "Not used with --sweep or --noise-breakdown (those define their own grids)."
        ),
    )
    ap.add_argument(
        "--disable-swap-typo-objective-v4",
        action="store_true",
        help=(
            "Disable canary default objective v4 for swap_typo and fall back to "
            "the legacy final-selection objective."
        ),
    )
    args = ap.parse_args()

    report, failures = run(
        seed=args.seed,
        samples=args.samples,
        beam_size=args.beam_size,
        noise_level=args.noise_level,
        scoring_mode=args.scoring_mode,
        forced_noise_mode=args.forced_noise_mode,
        swap_typo_objective_v4=not args.disable_swap_typo_objective_v4,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.fail_log.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.fail_log.open("w", encoding="utf-8") as f:
        for row in failures:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    out_msg = {
        "ok": True,
        "out": str(args.out),
        "fail_log": str(args.fail_log),
        "exact_restore_rate": report["exact_restore_rate"],
        "recovery_rate": report["recovery_rate"],
        "forced_noise_mode": args.forced_noise_mode,
        "swap_typo_objective_v4": report.get("swap_typo_objective_v4"),
    }
    if args.sweep:
        seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
        noise_levels = [float(x.strip()) for x in args.noise_levels.split(",") if x.strip()]
        sweep_doc = run_sweep(
            seeds=seeds,
            noise_levels=noise_levels,
            samples=args.samples,
            beam_size=args.beam_size,
            scoring_mode=args.scoring_mode,
        )
        args.sweep_out.parent.mkdir(parents=True, exist_ok=True)
        args.sweep_out.write_text(json.dumps(sweep_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out_msg["sweep_out"] = str(args.sweep_out)
        out_msg["determinism_delta"] = sweep_doc.get("aggregate", {}).get("determinism_delta")
        out_msg["sweep_min_exact_restore_rate"] = sweep_doc.get("aggregate", {}).get("min_exact_restore_rate")
    if args.noise_breakdown:
        seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
        nb_doc = run_noise_mode_breakdown(
            seeds=seeds,
            samples=args.samples,
            beam_size=args.beam_size,
            noise_level=args.noise_level,
            scoring_mode=args.scoring_mode,
        )
        args.noise_breakdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.noise_breakdown_out.write_text(json.dumps(nb_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out_msg["noise_breakdown_out"] = str(args.noise_breakdown_out)
        out_msg["hardest_mode"] = nb_doc.get("hardest_mode")
    print(json.dumps(out_msg, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
