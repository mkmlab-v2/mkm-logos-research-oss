#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import random
from math import factorial
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "trackb_quaternion_generalization_v6.json"


def _normalize(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q)
    return q / n if n > 0 else np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)


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


def _tok_q(tok: str, seed: int) -> np.ndarray:
    h = hashlib.sha256(f"{seed}:{tok}".encode("utf-8")).digest()
    vals = [int.from_bytes(h[i : i + 8], "big", signed=False) for i in range(0, 32, 8)]
    q = np.array([(v % 1000003) / 1000003.0 for v in vals], dtype=np.float64)
    return _normalize((q * 2.0) - 1.0)


def _encode_order(tokens: list[str], seed: int) -> np.ndarray:
    q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    for t in tokens:
        q = _qmul(q, _tok_q(t, seed))
    return _normalize(q)


def _encode_set(tokens: list[str], seed: int) -> np.ndarray:
    v = np.zeros(4, dtype=np.float64)
    for t in sorted(set(tokens)):
        v += _tok_q(t, seed)
    return _normalize(v)


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _jaccard_tokens(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _bigram_overlap(a: list[str], b: list[str]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ba = set(zip(a, a[1:]))
    bb = set(zip(b, b[1:]))
    if not ba and not bb:
        return 1.0
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def _position_alignment(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    hit = 0
    for i in range(n):
        if a[i] == b[i]:
            hit += 1
    return hit / n


def _adjacent_transposition_score(src: list[str], cand: list[str]) -> float:
    """
    Reward local adjacency consistency; penalize near swaps indirectly.
    Score in [0,1].
    """
    n = min(len(src), len(cand))
    if n < 3:
        return 0.0
    match = 0
    total = 0
    for i in range(n - 2):
        total += 1
        s_win = (src[i], src[i + 1], src[i + 2])
        c_win = (cand[i], cand[i + 1], cand[i + 2])
        if s_win == c_win:
            match += 1
        else:
            # partial credit: first/last aligned, middle may wobble
            if s_win[0] == c_win[0] and s_win[2] == c_win[2]:
                match += 0.5
    return match / total if total > 0 else 0.0


def _adjacent_swap_variants(tokens: list[str], limit: int = 24) -> list[list[str]]:
    if len(tokens) < 2:
        return []
    out: list[list[str]] = []
    for i in range(len(tokens) - 1):
        t = tokens[:]
        t[i], t[i + 1] = t[i + 1], t[i]
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _local_repair_variants(tokens: list[str], limit: int = 48) -> list[list[str]]:
    """
    Round3.5:
    Expand local repair space beyond adjacent swap.
    - adjacent swap
    - 2-hop move (i -> i+2 and i+2 -> i)
    - 3-token local rotate (left/right)
    """
    n = len(tokens)
    if n < 2:
        return []
    out: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def push(t: list[str]) -> None:
        if len(out) >= limit:
            return
        k = tuple(t)
        if k in seen:
            return
        seen.add(k)
        out.append(t)

    # 1) adjacent swaps
    for t in _adjacent_swap_variants(tokens, limit=limit):
        push(t)
        if len(out) >= limit:
            return out

    # 2) 2-hop moves
    if n >= 3:
        for i in range(n - 2):
            # i -> i+2
            t1 = tokens[:]
            x = t1.pop(i)
            t1.insert(i + 2, x)
            push(t1)
            if len(out) >= limit:
                return out
            # i+2 -> i
            t2 = tokens[:]
            y = t2.pop(i + 2)
            t2.insert(i, y)
            push(t2)
            if len(out) >= limit:
                return out

    # 3) 3-token local rotate
    if n >= 3:
        for i in range(n - 2):
            w = tokens[i : i + 3]
            # left rotate: abc -> bca
            t3 = tokens[:i] + [w[1], w[2], w[0]] + tokens[i + 3 :]
            push(t3)
            if len(out) >= limit:
                return out
            # right rotate: abc -> cab
            t4 = tokens[:i] + [w[2], w[0], w[1]] + tokens[i + 3 :]
            push(t4)
            if len(out) >= limit:
                return out
    return out


VOCAB = [
    "내가", "그가", "우리가", "팀이", "시스템이", "모델이", "시장", "위험", "점수", "정책",
    "분석", "요약", "검증", "생성", "전환", "신호", "관측", "규칙", "자본", "유동성",
    "금리", "전쟁", "패닉", "공급망", "유가", "데이터", "문서", "리포트", "알림", "권한",
    "인플레이션", "환율", "모멘텀", "변동성", "회귀", "추세", "보수", "공격", "위기", "완화",
]
OOV = ["ZXQ_001", "UNK_SIGMA", "OOV_TOKEN", "ALPHA_OMEGA", "NONLEX_777", "MISSING_404"]


def _make_sentence(rng: random.Random, length: int, oov_ratio: float) -> str:
    oov_n = int(round(length * oov_ratio))
    toks = [rng.choice(OOV) for _ in range(oov_n)] + [rng.choice(VOCAB) for _ in range(max(0, length - oov_n))]
    rng.shuffle(toks)
    return " ".join(toks)


def _permute(sentence: str, rng: random.Random) -> str:
    toks = sentence.split()
    if len(toks) > 1:
        i, j = rng.randrange(len(toks)), rng.randrange(len(toks))
        toks[i], toks[j] = toks[j], toks[i]
    return " ".join(toks)


def _local_reorders(tokens: list[str]) -> list[list[str]]:
    """
    Generate order-preserving local neighborhood candidates:
    - adjacent swap
    - one-token remove+insert (single move)
    """
    out: list[list[str]] = []
    n = len(tokens)
    if n <= 1:
        return out
    for i in range(n - 1):
        t = tokens[:]
        t[i], t[i + 1] = t[i + 1], t[i]
        out.append(t)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            t = tokens[:]
            tok = t.pop(i)
            t.insert(j, tok)
            out.append(t)
    # de-dup with order preserved
    uniq: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for t in out:
        k = tuple(t)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def _constructive_permutation_candidates(tokens: list[str], rng: random.Random, limit: int = 80) -> list[list[str]]:
    """
    Round2.3 constructive generator:
    - For short sequences, enumerate full permutation space (includes identity).
    - For longer sequences, sample permutation neighborhood around the identity.
    """
    n = len(tokens)
    if n <= 1:
        return [tokens[:]]
    out: list[list[str]] = []
    if n <= 5 and factorial(n) <= 240:
        for p in itertools.permutations(tokens, n):
            out.append(list(p))
        return out
    # sampled constructive candidates for longer lengths
    out.append(tokens[:])
    for _ in range(limit):
        t = tokens[:]
        i = rng.randrange(n)
        j = rng.randrange(n)
        t[i], t[j] = t[j], t[i]
        out.append(t)
    uniq: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for t in out:
        k = tuple(t)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def _blockwise_rebuild_candidates(tokens: list[str], block_size: int = 4) -> list[list[str]]:
    n = len(tokens)
    if n <= block_size:
        return [tokens[:]]
    blocks = [tokens[i : i + block_size] for i in range(0, n, block_size)]
    out: list[list[str]] = []
    # reorder blocks while preserving within-block order
    for perm in itertools.permutations(range(len(blocks))):
        merged: list[str] = []
        for idx in perm:
            merged.extend(blocks[idx])
        out.append(merged)
        if len(out) >= 120:
            break
    return out


def _beam_constructive_candidates(src_tokens: list[str], beam_size: int, limit: int = 120) -> list[list[str]]:
    n = len(src_tokens)
    if n <= 1:
        return [src_tokens[:]]
    rem0 = collections.Counter(src_tokens)
    beams: list[tuple[float, list[str], collections.Counter[str]]] = [(0.0, [], rem0)]
    def _prefix_order_consistency(prefix: list[str], target: list[str]) -> float:
        if not prefix:
            return 0.0
        pos_map: dict[str, list[int]] = {}
        for i, t in enumerate(target):
            pos_map.setdefault(t, []).append(i)
        seq_pos: list[int] = []
        for t in prefix:
            arr = pos_map.get(t)
            if not arr:
                continue
            seq_pos.append(arr[0])
        if len(seq_pos) <= 1:
            return 0.0
        ok = 0
        for i in range(1, len(seq_pos)):
            if seq_pos[i] >= seq_pos[i - 1]:
                ok += 1
        return ok / (len(seq_pos) - 1)

    for pos in range(n):
        nxt: list[tuple[float, list[str], collections.Counter[str]]] = []
        for score, prefix, rem in beams:
            for tok, cnt in rem.items():
                if cnt <= 0:
                    continue
                p2 = prefix + [tok]
                r2 = rem.copy()
                r2[tok] -= 1
                if r2[tok] == 0:
                    del r2[tok]
                s = score
                if tok == src_tokens[pos]:
                    s += 0.7
                if pos > 0 and p2[pos - 1] == src_tokens[pos - 1] and tok == src_tokens[pos]:
                    s += 0.3
                # Round2.7: reward monotonic prefix alignment to target order.
                s += 0.8 * _prefix_order_consistency(p2, src_tokens)
                nxt.append((s, p2, r2))
        nxt.sort(key=lambda x: x[0], reverse=True)
        beams = nxt[: max(1, beam_size)]
        if not beams:
            break
    out = [p for _, p, _ in beams if len(p) == n]
    if src_tokens not in out:
        out.append(src_tokens[:])
    return out[:limit]


def _chunkwise_beam_candidates(src_tokens: list[str], beam_size: int, limit: int = 160) -> list[list[str]]:
    """
    Round2.8: phrase/chunk-aware candidate construction.
    Build chunk units (size 2~3), then beam over chunk order with local order priors.
    """
    n = len(src_tokens)
    if n <= 3:
        return [src_tokens[:]]

    def _make_chunks(tokens: list[str], k: int) -> list[list[str]]:
        return [tokens[i : i + k] for i in range(0, len(tokens), k)]

    chunk_plans = [_make_chunks(src_tokens, 2), _make_chunks(src_tokens, 3)]
    out: list[list[str]] = []
    for chunks in chunk_plans:
        m = len(chunks)
        if m <= 1:
            out.append(src_tokens[:])
            continue
        beams: list[tuple[float, list[int], set[int]]] = [(0.0, [], set())]
        for step in range(m):
            nxt: list[tuple[float, list[int], set[int]]] = []
            for score, order, used in beams:
                for ci in range(m):
                    if ci in used:
                        continue
                    order2 = order + [ci]
                    used2 = set(used)
                    used2.add(ci)
                    s = score
                    # reward placing original chunk index close to original step
                    s += max(0.0, 1.0 - abs(ci - step) / max(1, m - 1))
                    # reward adjacent continuity in original chunk index
                    if len(order2) >= 2 and order2[-1] == order2[-2] + 1:
                        s += 0.4
                    nxt.append((s, order2, used2))
            nxt.sort(key=lambda x: x[0], reverse=True)
            beams = nxt[: max(1, beam_size)]
            if not beams:
                break
        for _, order, _ in beams:
            merged: list[str] = []
            for ci in order:
                merged.extend(chunks[ci])
            out.append(merged[:n])
    if src_tokens not in out:
        out.append(src_tokens[:])
    # de-dup preserve order
    uniq: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for t in out:
        k = tuple(t)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq[:limit]


def _build_candidates(
    src: str,
    length: int,
    oov_ratio: float,
    rng: random.Random,
    blockwise_mode: bool,
    block_size: int,
    beam_mode: bool,
    beam_size: int,
    chunkwise_mode: bool,
    chunk_beam_size: int,
) -> list[str]:
    # v6 candidate refinement:
    # - reduce random negatives
    # - include near-neighbor permutations and token-drop variants
    candidates: list[str] = []
    candidates.extend(_permute(src, rng) for _ in range(20))
    toks = src.split()
    # Sequence-preserving neighborhood search space
    local = _local_reorders(toks)
    candidates.extend(" ".join(t) for t in local[: min(24, len(local))])
    constructive = _constructive_permutation_candidates(toks, rng, limit=64)
    candidates.extend(" ".join(t) for t in constructive)
    if beam_mode and len(toks) >= 12:
        beamwise = _beam_constructive_candidates(toks, beam_size=beam_size, limit=160)
        candidates.extend(" ".join(t) for t in beamwise)
    if chunkwise_mode and len(toks) >= 12:
        chunkwise = _chunkwise_beam_candidates(toks, beam_size=chunk_beam_size, limit=200)
        candidates.extend(" ".join(t) for t in chunkwise)
    if blockwise_mode and len(toks) >= 12:
        blockwise = _blockwise_rebuild_candidates(toks, block_size=block_size)
        candidates.extend(" ".join(t) for t in blockwise)
    if len(toks) >= 3:
        for _ in range(8):
            t2 = toks[:]
            drop_idx = rng.randrange(len(t2))
            del t2[drop_idx]
            candidates.append(" ".join(t2))
    candidates.extend(_make_sentence(rng, length, oov_ratio) for _ in range(20))
    candidates = list(dict.fromkeys(candidates))
    return candidates


def _decode(
    order_q: np.ndarray,
    set_q: np.ndarray,
    src_tokens: list[str],
    candidates: list[str],
    seed: int,
    w_order: float,
    w_set: float,
    w_jac: float,
    w_bigram: float,
    w_sequence: float,
    semantic_fallback: bool,
    fallback_threshold: float,
    two_stage_ranker: bool,
    stage1_top_k: int,
    stage2_length_prior: bool,
    stage2_swap_guard: bool,
    stage2_swap_injection: bool,
    stage2_order_w_override: float,
    stage2_big_w_override: float,
    stage2_pos_w_override: float,
    stage2_inject_topn: int,
    stage2_inject_cap: int,
    stage2_repair_limit: int,
) -> tuple[str, float]:
    best = ""
    best_score = -10.0
    scored: list[tuple[str, float]] = []
    for c in candidates:
        toks = c.split()
        order_sim = _cos(order_q, _encode_order(toks, seed))
        set_sim = _cos(set_q, _encode_set(toks, seed))
        jac = _jaccard_tokens(src_tokens, toks)
        big = _bigram_overlap(src_tokens, toks)
        pos = _position_alignment(src_tokens, toks)
        s = (
            w_order * order_sim
            + w_set * set_sim
            + w_jac * jac
            + w_bigram * big
            + w_sequence * pos
        )
        scored.append((c, s))
        if s > best_score:
            best, best_score = c, s
    # Round2.2: two-stage ranker for sequence recovery in blind setting.
    # Stage1 narrows by semantic/set compatibility, Stage2 re-ranks by order-only signals.
    if two_stage_ranker and scored:
        stage1 = []
        for c, _ in scored:
            toks = c.split()
            set_sim = _cos(set_q, _encode_set(toks, seed))
            jac = _jaccard_tokens(src_tokens, toks)
            stage1_score = 0.7 * set_sim + 0.3 * jac
            stage1.append((c, stage1_score))
        stage1.sort(key=lambda x: x[1], reverse=True)
        k = max(1, min(stage1_top_k, len(stage1)))
        shortlist = [c for c, _ in stage1[:k]]
        if stage2_swap_injection and shortlist:
            # Round3.2/3.5: inject local-repair candidates directly into stage2 pool.
            inject: list[str] = []
            topn = max(1, stage2_inject_topn)
            cap = max(8, stage2_inject_cap)
            repair_limit = max(4, stage2_repair_limit)
            for base in shortlist[: min(topn, len(shortlist))]:
                bt = base.split()
                for vt in _local_repair_variants(bt, limit=repair_limit):
                    inject.append(" ".join(vt))
                    if len(inject) >= cap:
                        break
                if len(inject) >= cap:
                    break
            shortlist = list(dict.fromkeys(shortlist + inject))
        ts_best = best
        ts_best_score = -10.0
        n_tokens = len(src_tokens)
        order_w = 0.6
        big_w = 0.2
        pos_w = 0.2
        if stage2_length_prior:
            # Round2.9: length-aware hard prior for long-sequence stabilization.
            if n_tokens >= 20:
                order_w, big_w, pos_w = 0.35, 0.15, 0.50
            elif n_tokens >= 16:
                order_w, big_w, pos_w = 0.45, 0.20, 0.35
            elif n_tokens >= 12:
                order_w, big_w, pos_w = 0.55, 0.20, 0.25
        if stage2_order_w_override >= 0.0:
            order_w = stage2_order_w_override
        if stage2_big_w_override >= 0.0:
            big_w = stage2_big_w_override
        if stage2_pos_w_override >= 0.0:
            pos_w = stage2_pos_w_override
        for c in shortlist:
            toks = c.split()
            order_sim = _cos(order_q, _encode_order(toks, seed))
            big = _bigram_overlap(src_tokens, toks)
            pos = _position_alignment(src_tokens, toks)
            stage2_score = order_w * order_sim + big_w * big + pos_w * pos
            if stage2_swap_guard:
                trans = _adjacent_transposition_score(src_tokens, toks)
                stage2_score += 0.25 * trans
            if stage2_score > ts_best_score:
                ts_best = c
                ts_best_score = stage2_score
        # Keep confidence output scale comparable by returning original blended score.
        for c, s in scored:
            if c == ts_best:
                return c, s
        return ts_best, best_score
    # Minimal semantic fallback (experiment lane only):
    # if confidence is low, re-rank by token-set preservation first.
    if semantic_fallback and best_score < fallback_threshold and scored:
        fb_best = best
        fb_score = -1.0
        for c, _s in scored:
            toks = c.split()
            jac = _jaccard_tokens(src_tokens, toks)
            big = _bigram_overlap(src_tokens, toks)
            # Preserve lexical set first, then local order consistency.
            rank = jac * 0.9 + big * 0.1
            if rank > fb_score:
                fb_best = c
                fb_score = rank
        return fb_best, best_score
    return best, best_score


def _evaluate_short(
    seeds: list[int],
    samples_per_cell: int,
    weights: tuple[float, float, float, float],
    semantic_fallback: bool,
    fallback_threshold: float,
    eval_metric: str,
    w_sequence: float,
    include_target_in_candidates: bool,
    two_stage_ranker: bool,
    stage1_top_k: int,
    lengths: list[int],
    oov_ratios: list[float],
    blockwise_mode: bool,
    block_size: int,
    beam_mode: bool,
    beam_size: int,
    chunkwise_mode: bool,
    chunk_beam_size: int,
    stage2_length_prior: bool,
    collect_failures: bool,
    failure_limit: int,
    stage2_swap_guard: bool,
    stage2_swap_injection: bool,
    stage2_order_w_override: float,
    stage2_big_w_override: float,
    stage2_pos_w_override: float,
    stage2_inject_topn: int,
    stage2_inject_cap: int,
    stage2_repair_limit: int,
) -> dict[str, Any]:
    w_order, w_set, w_jac, w_bigram = weights
    curve: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for length in lengths:
        for oov_ratio in oov_ratios:
            total = ok = 0
            for seed in seeds:
                rng = random.Random(seed * 10000 + length * 100 + int(oov_ratio * 1000))
                for _ in range(samples_per_cell):
                    src = _make_sentence(rng, length, oov_ratio)
                    toks = src.split()
                    oq = _encode_order(toks, seed)
                    sq = _encode_set(toks, seed)
                    cands = _build_candidates(
                        src,
                        length,
                        oov_ratio,
                        rng,
                        blockwise_mode,
                        block_size,
                        beam_mode,
                        beam_size,
                        chunkwise_mode,
                        chunk_beam_size,
                    )
                    # For sequence recovery eval, the canonical target must exist in candidate space.
                    # Otherwise exact-sequence metric is structurally forced to zero.
                    if eval_metric == "exact_sequence" and include_target_in_candidates:
                        cands = [src] + cands
                    if not cands:
                        continue
                    dec, _ = _decode(
                        oq,
                        sq,
                        toks,
                        cands,
                        seed,
                        w_order,
                        w_set,
                        w_jac,
                        w_bigram,
                        w_sequence,
                        semantic_fallback,
                        fallback_threshold,
                        two_stage_ranker,
                        stage1_top_k,
                        stage2_length_prior,
                        stage2_swap_guard,
                        stage2_swap_injection,
                        stage2_order_w_override,
                        stage2_big_w_override,
                        stage2_pos_w_override,
                        stage2_inject_topn,
                        stage2_inject_cap,
                        stage2_repair_limit,
                    )
                    total += 1
                    if eval_metric == "exact_sequence":
                        if dec == src:
                            ok += 1
                        elif collect_failures and len(failures) < failure_limit:
                            failures.append(
                                {
                                    "seed": seed,
                                    "length": length,
                                    "oov_ratio": oov_ratio,
                                    "source": src,
                                    "decoded": dec,
                                }
                            )
                    else:
                        if set(dec.split()) == set(toks):
                            ok += 1
            rate = (ok / total) if total else 0.0
            rate_key = "exact_sequence_match_rate" if eval_metric == "exact_sequence" else "token_set_match_rate"
            curve.append({"length": length, "oov_ratio": oov_ratio, "sample_count": total, rate_key: rate})
    rate_key = "exact_sequence_match_rate" if eval_metric == "exact_sequence" else "token_set_match_rate"
    min_rate = min(c[rate_key] for c in curve) if curve else 0.0
    return {"curve": curve, "min_rate": min_rate, "failures": failures}


def _resolve_harness_mode(mode: str, args: argparse.Namespace) -> dict[str, Any]:
    """
    Split distill/restore harness mode for Track B experimentation.
    - semantic_restore_only: token-set restore with semantic fallback emphasis.
    - exact_restore_guarded: exact-sequence restore with guardrails/failure capture.
    """
    if mode == "semantic_restore_only":
        return {
            "eval_metric": "token_set",
            "include_target_in_candidates": False,
            "semantic_fallback": True,
            "collect_failures": False,
        }
    if mode == "exact_restore_guarded":
        return {
            "eval_metric": "exact_sequence",
            "include_target_in_candidates": True,
            "semantic_fallback": bool(args.semantic_fallback),
            "collect_failures": bool(args.failure_log.strip()),
        }
    # auto: retain CLI behavior for backward compatibility.
    return {
        "eval_metric": args.eval_metric,
        "include_target_in_candidates": bool(args.include_target_in_candidates),
        "semantic_fallback": bool(args.semantic_fallback),
        "collect_failures": bool(args.failure_log.strip()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B v6 refined candidate + weight grid bench.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seeds", default="7,13,29")
    ap.add_argument("--samples-per-cell", type=int, default=60)
    ap.add_argument("--semantic-fallback", action="store_true")
    ap.add_argument("--fallback-threshold", type=float, default=0.85)
    ap.add_argument("--eval-metric", choices=("token_set", "exact_sequence"), default="token_set")
    ap.add_argument("--sequence-weight", type=float, default=0.3)
    ap.add_argument("--include-target-in-candidates", action="store_true")
    ap.add_argument("--two-stage-ranker", action="store_true")
    ap.add_argument("--stage1-top-k", type=int, default=12)
    ap.add_argument("--lengths", default="3,5")
    ap.add_argument("--oov-ratios", default="0.0,0.1")
    ap.add_argument("--single-profile", action="store_true")
    ap.add_argument("--blockwise-mode", action="store_true")
    ap.add_argument("--block-size", type=int, default=4)
    ap.add_argument("--beam-mode", action="store_true")
    ap.add_argument("--beam-size", type=int, default=6)
    ap.add_argument("--chunkwise-mode", action="store_true")
    ap.add_argument("--chunk-beam-size", type=int, default=8)
    ap.add_argument("--stage2-length-prior", action="store_true")
    ap.add_argument("--stage2-swap-guard", action="store_true")
    ap.add_argument("--stage2-swap-injection", action="store_true")
    ap.add_argument("--stage2-order-w", type=float, default=-1.0)
    ap.add_argument("--stage2-big-w", type=float, default=-1.0)
    ap.add_argument("--stage2-pos-w", type=float, default=-1.0)
    ap.add_argument("--stage2-inject-topn", type=int, default=8)
    ap.add_argument("--stage2-inject-cap", type=int, default=96)
    ap.add_argument("--stage2-repair-limit", type=int, default=12)
    ap.add_argument("--failure-log", default="")
    ap.add_argument("--failure-limit", type=int, default=200)
    ap.add_argument(
        "--harness-mode",
        choices=("auto", "semantic_restore_only", "exact_restore_guarded"),
        default="auto",
        help="Split distill/restore harness mode for Track B.",
    )
    args = ap.parse_args()
    harness = _resolve_harness_mode(args.harness_mode, args)


    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    lengths = [int(x.strip()) for x in args.lengths.split(",") if x.strip()]
    oov_ratios = [float(x.strip()) for x in args.oov_ratios.split(",") if x.strip()]

    # Focus grid for short-length recovery
    if args.single_profile:
        w_orders = [0.30]
        w_sets = [0.35]
        w_jacs = [0.20]
        w_bigrams = [0.05]
    else:
        w_orders = [0.30, 0.35, 0.40]
        w_sets = [0.35, 0.40, 0.45]
        w_jacs = [0.20, 0.25]
        w_bigrams = [0.05, 0.10]

    tried: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_score = -1.0
    for w_order, w_set, w_jac, w_bigram in itertools.product(w_orders, w_sets, w_jacs, w_bigrams):
        if w_order + w_set + w_jac + w_bigram > 1.2:
            continue
        eval_res = _evaluate_short(
            seeds,
            args.samples_per_cell,
            (w_order, w_set, w_jac, w_bigram),
            harness["semantic_fallback"],
            args.fallback_threshold,
            harness["eval_metric"],
            args.sequence_weight,
            harness["include_target_in_candidates"],
            args.two_stage_ranker,
            args.stage1_top_k,
            lengths,
            oov_ratios,
            args.blockwise_mode,
            args.block_size,
            args.beam_mode,
            args.beam_size,
            args.chunkwise_mode,
            args.chunk_beam_size,
            args.stage2_length_prior,
            harness["collect_failures"],
            args.failure_limit,
            args.stage2_swap_guard,
            args.stage2_swap_injection,
            args.stage2_order_w,
            args.stage2_big_w,
            args.stage2_pos_w,
            args.stage2_inject_topn,
            args.stage2_inject_cap,
            args.stage2_repair_limit,
        )
        row = {
            "weights": {
                "order": w_order,
                "set": w_set,
                "jaccard": w_jac,
                "bigram": w_bigram,
            },
            "min_short_bucket_rate": eval_res["min_rate"],
            "curve": eval_res["curve"],
            "failures": eval_res.get("failures", []),
        }
        tried.append(row)
        if eval_res["min_rate"] > best_score:
            best_score = eval_res["min_rate"]
            best = row

    out = {
        "schema": "trackb_quaternion_generalization_v6",
        "mode": "short_length_candidate_refine_weight_grid",
        "seeds": seeds,
        "samples_per_cell": args.samples_per_cell,
        "semantic_fallback": bool(args.semantic_fallback),
        "harness_mode": args.harness_mode,
        "resolved_harness": harness,
        "fallback_threshold": float(args.fallback_threshold),
        "eval_metric": harness["eval_metric"],
        "sequence_weight": float(args.sequence_weight),
        "include_target_in_candidates": bool(harness["include_target_in_candidates"]),
        "two_stage_ranker": bool(args.two_stage_ranker),
        "stage1_top_k": int(args.stage1_top_k),
        "lengths": lengths,
        "oov_ratios": oov_ratios,
        "single_profile": bool(args.single_profile),
        "blockwise_mode": bool(args.blockwise_mode),
        "block_size": int(args.block_size),
        "beam_mode": bool(args.beam_mode),
        "beam_size": int(args.beam_size),
        "chunkwise_mode": bool(args.chunkwise_mode),
        "chunk_beam_size": int(args.chunk_beam_size),
        "stage2_length_prior": bool(args.stage2_length_prior),
        "stage2_swap_guard": bool(args.stage2_swap_guard),
        "stage2_swap_injection": bool(args.stage2_swap_injection),
        "stage2_order_w_override": float(args.stage2_order_w),
        "stage2_big_w_override": float(args.stage2_big_w),
        "stage2_pos_w_override": float(args.stage2_pos_w),
        "stage2_inject_topn": int(args.stage2_inject_topn),
        "stage2_inject_cap": int(args.stage2_inject_cap),
        "stage2_repair_limit": int(args.stage2_repair_limit),
        "grid_size": len(tried),
        "best": best,
        "target_threshold": 0.95,
        "target_passed": bool(best and best.get("min_short_bucket_rate", 0.0) >= 0.95),
        "top5": sorted(tried, key=lambda x: x["min_short_bucket_rate"], reverse=True)[:5],
    }
    if args.failure_log.strip():
        flog = Path(args.failure_log)
        flog.parent.mkdir(parents=True, exist_ok=True)
        rows: list[str] = []
        for item in tried:
            for f in item.get("failures", []):
                payload = {
                    "schema": "trackb_quaternion_failure_case_v1",
                    "weights": item.get("weights", {}),
                    **f,
                }
                rows.append(json.dumps(payload, ensure_ascii=False))
        flog.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        out["failure_log"] = str(flog)
        out["failure_count"] = sum(len(item.get("failures", [])) for item in tried)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "best_min_short_bucket_rate": best_score, "target_passed": out["target_passed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
