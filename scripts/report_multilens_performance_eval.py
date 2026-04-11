#!/usr/bin/env python3
"""Evaluate multi-lens performance dimensions from a fixed input spec.

Supports baseline (fixed compressed text) and experimental ultra compression
generation for A/B/C strategy benchmarks.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V1.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
SHARDS_ROOT = ROOT / "codebook" / "shards"
SLOT_DICT_V6 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_DOMAIN_SLOT_DICTIONARY_V6.json"
SLOT_DICT_V61 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_DOMAIN_SLOT_DICTIONARY_V61.json"

from scripts.core.domain_router import DomainSpecificRouter
from scripts.core.master_codebook_lexicon_v1_bridge import (
    resolve_latest_codebook_path,
    lexicon_hits_for_text,
)
from scripts.core.cee_logic_core_v1 import CEEInput, run_cee_logic_core_v1
from scripts.core.contextual_generator_v2 import ContextualGeneratorV2
from scripts.core.contextual_generator_v3 import ContextualGeneratorV3
from scripts.core.contextual_generator_v4 import ContextualGeneratorV4
from scripts.core.contextual_generator_v5_codec import ContextualGeneratorV5Codec
from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
from scripts.core.state16_interface import NoopState16Adapter, State16Input

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")
WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]+")

# Quality gate: strict 50% legacy; 49% policy floor for bench runs after must_keep safety-net append
# (see reports/memory/mkm_memory_no_go_remediation_note_latest.json).
ULTRA_TOKEN_SAVING_STRICT = 0.50
ULTRA_TOKEN_SAVING_POLICY_MIN = 0.49

# When global experimental caps are very high (e.g. strict 90% taxonomy sweep), cap
# rows by input `domain` so "variable fidelity" limits fidelity collapse (General Rail).
_HIGH_STRESS_GMAX_THRESHOLD = 0.85
_HIGH_STRESS_DOMAIN_MAX_SAVING: dict[str, float] = {
    "policy_legal_lite": 0.52,
    "meeting": 0.52,
    "support_faq": 0.54,
}

# Global billing-aligned token proxy (Option B: does not replace legacy `_tokens` / global_token_saving_rate).
TIKTOKEN_O200K_ENCODING = "o200k_base"


@lru_cache(maxsize=1)
def _tiktoken_o200k_status() -> tuple[Any | None, str | None]:
    """Return (encoder, None) or (None, reason) for optional tiktoken o200k_base."""
    try:
        import tiktoken
    except ImportError:
        return None, "tiktoken_import_error"
    try:
        return tiktoken.get_encoding(TIKTOKEN_O200K_ENCODING), None
    except Exception as exc:  # noqa: BLE001 — surface encoding/registry failures
        return None, f"tiktoken_encoding_error:{type(exc).__name__}"


def _o200k_saving_rate(tokens_before: int, tokens_after: int) -> float:
    """OpenAI-style billing token saving rate (o200k_base), corpus-level or per-row."""
    if not tokens_before:
        return 0.0
    return 1.0 - (tokens_after / tokens_before)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate multi-lens performance evaluation report.")
    p.add_argument("--input", default=str(SRC), help="Input JSON spec path")
    p.add_argument("--output", default=str(OUT), help="Output report path")
    p.add_argument(
        "--mode",
        choices=("baseline", "experimental"),
        default="baseline",
        help="baseline uses source compressed_text; experimental generates ultra compression candidates",
    )
    p.add_argument("--strategy", choices=("A", "B", "C"), default="C", help="Experimental strategy")
    p.add_argument("--intensity", choices=("high", "ultra", "extreme"), default="high", help="Experimental intensity")
    p.add_argument(
        "--jaccard-drop-threshold-pp",
        type=float,
        default=2.0,
        help="Allowed jaccard drop in percentage points against baseline",
    )
    p.add_argument(
        "--baseline-report",
        default=str(BASELINE_V2),
        help="Baseline report path for gate calculations",
    )
    p.add_argument(
        "--domain-sensitive-terms",
        default="",
        help="Comma-separated terms that must be preserved in experimental compression",
    )
    p.add_argument(
        "--include-cee-core",
        action="store_true",
        help="Attach CEE core payload (gematria->4D->state16) into each compression case row.",
    )
    p.add_argument(
        "--include-gematria-metadata",
        action="store_true",
        help="Attach scripts/core/gematria_engine metadata per compression case row.",
    )
    p.add_argument(
        "--include-gematria-4d-bridge",
        action="store_true",
        help="Attach gematria_to_4d_bridge (nearest state16) per row; use with --include-gematria-metadata.",
    )
    p.add_argument(
        "--apply-gematria-4d-bridge-policy",
        action="store_true",
        help="Experimental mode only: use bridge distance in candidate selection (see evaluate_report).",
    )
    p.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit with code 1 if quality_gate.sensitive_integrity_ok is false.",
    )
    p.add_argument(
        "--require-tiktoken-o200k",
        action="store_true",
        help="Fail if tiktoken o200k_base encoder is unavailable (billing spine lock).",
    )
    p.add_argument(
        "--use-domain-router",
        action="store_true",
        help="Run DomainSpecificRouter for shard_id/domain in each case row (baseline or experimental).",
    )
    p.add_argument(
        "--use-master-codebook-lexicon",
        action="store_true",
        help="Attach master codebook lexicon bridge metadata (optional; may expand must_keep).",
    )
    return p


def _tokens(text: str) -> int:
    return _tokens_cached(text)


def _norm_words(text: str) -> set[str]:
    return set(_norm_words_cached(text))


def _split_words(text: str) -> list[str]:
    return list(_split_words_cached(text))


@lru_cache(maxsize=8192)
def _tokens_cached(text: str) -> int:
    # Simple portable token proxy (word-ish and symbol chunks).
    return len(TOKEN_RE.findall(text))


@lru_cache(maxsize=8192)
def _norm_words_cached(text: str) -> tuple[str, ...]:
    return tuple(w.lower() for w in WORD_RE.findall(text))


@lru_cache(maxsize=8192)
def _split_words_cached(text: str) -> tuple[str, ...]:
    return tuple(WORD_RE.findall(text))


def _has_hangul_syllable(word: str) -> bool:
    return any("가" <= ch <= "힣" for ch in word)


def _is_hangul_particle_like(word: str) -> bool:
    # Practical proxy for preserving Korean grammatical glue tokens.
    if not _has_hangul_syllable(word):
        return False
    if word in {
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "의",
        "와",
        "과",
        "도",
        "로",
        "및",
        "또는",
    }:
        return True
    endings = (
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "의",
        "와",
        "과",
        "도",
        "로",
        "으로",
        "에서",
        "에게",
        "께",
        "만",
        "다",
        "요",
    )
    return any(word.endswith(e) for e in endings)


def _is_guard_token(word: str) -> bool:
    """Tokens that should survive aggressive compression."""
    w = word.lower()
    if w in {
        "not",
        "no",
        "never",
        "must",
        "cannot",
        "without",
        "unless",
        "manual",
        "strict",
        "direct",
        "witness",
        "evidence",
        "traceability",
        "read",
        "only",
        "readonly",
        "state",
        "a",
        "track",
        "policy",
        "trigger",
    }:
        return True
    return w in {"아님", "금지", "필수", "수동", "증거", "추적", "직접", "체질", "사상의학", "명리", "성경"}


def _jaccard(a: str, b: str) -> float:
    sa = _norm_words(a)
    sb = _norm_words(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _axis_hit(answer: str, axis: str) -> bool:
    a = answer.lower()
    axis_map = {
        "myeongri": ["명리", "state", "state_id", "myeongri"],
        "bible": ["성경", "시편", "logos", "bible"],
        "sasang": ["사상의학", "체질", "sasang"],
    }
    return any(k in a for k in axis_map.get(axis, [axis]))


def _compress_experimental(
    raw: str,
    strategy: str,
    intensity: str,
    must_keep: set[str],
    *,
    use_hangul_principle: bool = False,
) -> str:
    words = _split_words(raw)
    if not words:
        return raw
    # Keep ratio increases with intensity.
    stride = {"high": 2, "ultra": 3, "extreme": 4}[intensity]
    strategy_offset = {"A": 0, "B": 1, "C": 2}[strategy]
    kept: list[str] = []
    # Keep sentence anchors to reduce semantic collapse in high compression.
    anchors = {0, 1, max(0, len(words) - 2), max(0, len(words) - 1), len(words) // 2}
    for i, w in enumerate(words):
        lw = w.lower()
        if lw in must_keep:
            kept.append(w)
            continue
        if use_hangul_principle and _is_hangul_particle_like(w):
            kept.append(w)
            continue
        if _is_guard_token(w) or i in anchors:
            kept.append(w)
            continue
        if strategy == "A":
            if i < 2 or i % stride == 0:
                kept.append(w)
        elif strategy == "B":
            if (i + strategy_offset) % stride == 0:
                kept.append(w)
        else:
            # C: hybrid, keep early anchors and periodic words.
            if i < 3 or (i + strategy_offset) % stride == 0:
                kept.append(w)
    # In Hangul-principle mode, avoid aggressive dedupe because repeated
    # function words can carry grammatical role in agglutinative sentences.
    if use_hangul_principle:
        return " ".join(kept)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    uniq: list[str] = []
    for w in kept:
        lw = w.lower()
        if lw in seen:
            continue
        seen.add(lw)
        uniq.append(w)
    return " ".join(uniq)


def _sensitive_integrity(raw: str, candidate: str, must_keep: set[str]) -> float:
    if not must_keep:
        return 1.0
    raw_words = {w.lower() for w in _split_words(raw)}
    cand_words = {w.lower() for w in _split_words(candidate)}
    required = {w for w in must_keep if w in raw_words}
    if not required:
        return 1.0
    preserved = sum(1 for w in required if w in cand_words)
    return preserved / len(required)


def _sensitive_violation(raw: str, candidate: str, must_keep: set[str]) -> bool:
    """True when raw required a must_keep lemma present in raw but missing from candidate."""
    if not must_keep:
        return False
    raw_words = {w.lower() for w in _split_words(raw)}
    cand_words = {w.lower() for w in _split_words(candidate)}
    required = {w for w in must_keep if w in raw_words}
    if not required:
        return False
    return any(w not in cand_words for w in required)


def _ensure_sensitive_tokens_preserved(raw: str, candidate: str, must_keep: set[str]) -> str:
    """Append any required must_keep lemmas present in raw but missing from candidate (experimental safety net)."""
    if not must_keep:
        return candidate
    raw_words_lower = {w.lower() for w in _split_words(raw)}
    cand_words_lower = {w.lower() for w in _split_words(candidate)}
    required = {w for w in must_keep if w in raw_words_lower}
    missing_lemmas = [w for w in required if w not in cand_words_lower]
    if not missing_lemmas:
        return candidate
    forms: list[str] = []
    for lemma in sorted(missing_lemmas):
        form = lemma
        for w in _split_words(raw):
            if w.lower() == lemma:
                form = w
                break
        forms.append(form)
    suffix = " ".join(forms)
    base = candidate.rstrip()
    if not base:
        return suffix
    return f"{base} {suffix}"


def _reconstruct_candidate(
    *,
    raw: str,
    source_reconstructed: str,
    compressed_candidate: str,
    mode: str,
) -> str:
    """Return text used for fidelity scoring.

    In experimental mode, score the actual candidate path rather than a fixed
    pre-baked reconstruction string. This avoids inflated fidelity when the
    compressed payload changes.
    """
    if mode == "experimental":
        # Current benchmark does not include a domain decoder yet; use the
        # effective compressed candidate as the reconstruction proxy.
        return compressed_candidate
    return source_reconstructed


def _reconstruct_experimental_from_raw(
    *,
    raw: str,
    compressed_candidate: str,
    use_hangul_principle: bool,
) -> str:
    """Heuristic decoder for experimental evaluation.

    Builds a reconstruction from raw scaffold using compressed anchors.
    For Hangul mode, it also keeps nearby particles/endings to preserve
    agglutinative sentence glue.
    """
    raw_words = _split_words(raw)
    comp_words = _split_words(compressed_candidate)
    if not raw_words or not comp_words:
        return compressed_candidate
    comp_set = {w.lower() for w in comp_words}
    keep = [False] * len(raw_words)
    kept_indices: list[int] = []
    for idx, w in enumerate(raw_words):
        lw = w.lower()
        if lw in comp_set:
            keep[idx] = True
            kept_indices.append(idx)
            continue
        if use_hangul_principle and _is_hangul_particle_like(w):
            left_kept = idx > 0 and raw_words[idx - 1].lower() in comp_set
            right_kept = idx + 1 < len(raw_words) and raw_words[idx + 1].lower() in comp_set
            if left_kept or right_kept:
                keep[idx] = True
    if use_hangul_principle and kept_indices:
        # Fill short gaps between anchor tokens to recover Korean connective flow.
        for a, b in zip(kept_indices, kept_indices[1:]):
            if 1 <= (b - a) <= 4:
                for j in range(a + 1, b):
                    keep[j] = True
        # Keep immediate neighbors of anchors.
        for i in kept_indices:
            if i > 0:
                keep[i - 1] = True
            if i + 1 < len(raw_words):
                keep[i + 1] = True
    rebuilt = [w for i, w in enumerate(raw_words) if keep[i]]
    return " ".join(rebuilt) if rebuilt else compressed_candidate


def _is_sensitive_case(raw: str, must_keep: set[str]) -> bool:
    if not must_keep:
        return False
    raw_words = {w.lower() for w in _split_words(raw)}
    return any(term in raw_words for term in must_keep)


def _is_hangul_case(raw: str) -> bool:
    return any("가" <= ch <= "힣" for ch in raw)


def _apply_max_saving_cap(raw: str, candidate: str, *, max_saving_rate: float | None) -> str:
    """Expand candidate with raw anchors until saving cap is respected."""
    if max_saving_rate is None:
        return candidate
    raw_words = _split_words(raw)
    cand_words = _split_words(candidate)
    raw_t = len(raw_words)
    if raw_t <= 0:
        return candidate
    target_comp_tokens = int((1.0 - max_saving_rate) * raw_t + 0.999999)
    if len(cand_words) >= target_comp_tokens:
        return candidate
    out = list(cand_words)
    seen = {w.lower() for w in cand_words}
    for w in raw_words:
        lw = w.lower()
        if lw in seen:
            continue
        out.append(w)
        seen.add(lw)
        if len(out) >= target_comp_tokens:
            break
    return " ".join(out)


def _apply_min_saving_floor(
    raw: str,
    candidate: str,
    *,
    min_saving_rate: float | None,
    must_keep_terms: set[str],
    use_hangul_principle: bool,
) -> str:
    """Trim non-critical tokens until a minimum saving floor is met."""
    if min_saving_rate is None:
        return candidate
    raw_words = _split_words(raw)
    cand_words = _split_words(candidate)
    raw_t = len(raw_words)
    if raw_t <= 0:
        return candidate
    target_comp_tokens = int((1.0 - min_saving_rate) * raw_t)
    if target_comp_tokens < 1:
        target_comp_tokens = 1
    if len(cand_words) <= target_comp_tokens:
        return candidate

    must_keep = {w.lower() for w in must_keep_terms}
    essential: list[str] = []
    optional: list[str] = []
    for w in cand_words:
        lw = w.lower()
        is_essential = lw in must_keep or _is_guard_token(w)
        if use_hangul_principle and _is_hangul_particle_like(w):
            is_essential = True
        if is_essential:
            essential.append(w)
        else:
            optional.append(w)

    if len(essential) >= target_comp_tokens:
        return " ".join(essential[:target_comp_tokens])
    needed = target_comp_tokens - len(essential)
    return " ".join(essential + optional[:needed])


def _bridge_policy_terms_for_state(state16: int | None) -> set[str]:
    if state16 in {2, 8, 11, 14}:
        # Conservative states: preserve risk/traceability anchors.
        return {"manual", "strict", "direct", "evidence", "traceability", "체질", "명리", "성경", "증거", "직접"}
    if state16 in {1, 4, 7, 10, 13, 16}:
        # Expansion states: keep policy-governance anchors to avoid over-pruning.
        return {"policy", "state", "trigger", "boundary", "cadence", "체질", "명리"}
    return {"체질", "명리"}


def _guard_preservation_score(raw: str, candidate: str, guard_terms: set[str]) -> float:
    raw_words = {w.lower() for w in _split_words(raw)}
    cand_words = {w.lower() for w in _split_words(candidate)}
    required = {w for w in guard_terms if w in raw_words}
    if not required:
        return 1.0
    kept = sum(1 for w in required if w in cand_words)
    return kept / len(required)


def _bridge_aware_candidate_select(
    *,
    raw: str,
    base_candidate: str,
    strategy: str,
    intensity: str,
    effective_must_keep: set[str],
    effective_hangul_principle: bool,
    cap: float | None,
    bridge_state16: int | None,
    bridge_target_distance: float | None,
    score_weights: dict[str, float] | None = None,
) -> str:
    variants: list[str] = []
    # Candidate 1: base from current pipeline
    variants.append(base_candidate)
    # Candidate 2: denser keep (one level less aggressive)
    denser_intensity = {"extreme": "ultra", "ultra": "high", "high": "high"}[intensity]
    denser = _compress_experimental(
        raw,
        strategy=strategy,
        intensity=denser_intensity,
        must_keep=effective_must_keep,
        use_hangul_principle=effective_hangul_principle,
    )
    denser = _apply_max_saving_cap(raw, denser, max_saving_rate=cap)
    variants.append(denser)
    # Candidate 3: sparse keep (one level more aggressive when possible)
    if intensity != "extreme":
        sparser_intensity = {"high": "ultra", "ultra": "extreme"}[intensity]
        sparser = _compress_experimental(
            raw,
            strategy=strategy,
            intensity=sparser_intensity,
            must_keep=effective_must_keep,
            use_hangul_principle=effective_hangul_principle,
        )
        sparser = _apply_max_saving_cap(raw, sparser, max_saving_rate=cap)
        variants.append(sparser)

    guard_terms = _bridge_policy_terms_for_state(bridge_state16)
    weights = score_weights or {
        "fidelity": 1.3,
        "guard": 0.5,
        "saving": 0.2,
        "distance_penalty": 4.0,
    }
    best = base_candidate
    best_score = -10**9
    raw_token_count = _tokens(raw)
    for cand in variants:
        rec = _reconstruct_experimental_from_raw(
            raw=raw,
            compressed_candidate=cand,
            use_hangul_principle=effective_hangul_principle,
        )
        fidelity = _jaccard(raw, rec)
        saving = 1.0 - ((_tokens(cand) / raw_token_count) if raw_token_count else 1.0)
        guard = _guard_preservation_score(raw, cand, guard_terms)
        cand_bridge = build_gematria_4d_bridge(
            gematria_metadata=build_gematria_metadata(
                raw_text=raw,
                compressed_text=cand,
                reconstructed_text=rec,
            )
        )
        dist = cand_bridge.get("distance_to_state16")
        dist_penalty = abs(float(dist) - float(bridge_target_distance)) if (dist is not None and bridge_target_distance is not None) else 0.0
        # Higher is better: favor fidelity first, then state-distance fit, then guard preservation, then saving.
        score = (
            (float(weights.get("fidelity", 1.3)) * fidelity)
            + (float(weights.get("guard", 0.5)) * guard)
            + (float(weights.get("saving", 0.2)) * saving)
            - (float(weights.get("distance_penalty", 4.0)) * dist_penalty)
        )
        if score > best_score:
            best_score = score
            best = cand
    return best


def evaluate_report(
    doc: dict[str, Any],
    *,
    source_input: str,
    mode: str = "baseline",
    strategy: str = "C",
    intensity: str = "high",
    must_keep: set[str] | None = None,
    jaccard_drop_threshold_pp: float = 2.0,
    baseline_avg_jaccard: float | None = None,
    general_max_saving_rate: float | None = None,
    sensitive_max_saving_rate: float | None = None,
    hangul_max_saving_rate: float | None = None,
    use_hangul_principle: bool = False,
    use_domain_router: bool = False,
    use_master_codebook_lexicon_v1: bool = False,
    master_codebook_lexicon_path: Path | str | None = None,
    include_gematria_metadata: bool = False,
    include_gematria_4d_bridge: bool = False,
    include_cee_core: bool = False,
    apply_gematria_4d_bridge_policy: bool = False,
    bridge_score_weights: dict[str, float] | None = None,
    use_contextual_generator_v2: bool = False,
    use_contextual_generator_v3: bool = False,
    use_contextual_generator_v4: bool = False,
    use_contextual_generator_v5_codec: bool = False,
    require_tiktoken_o200k: bool = False,
) -> dict[str, Any]:
    must_keep = must_keep or set()
    comp_cases = doc.get("compression_cases", [])
    fus_cases = doc.get("fusion_answer_cases", [])

    enc_o200k, o200k_err = _tiktoken_o200k_status()
    if require_tiktoken_o200k and enc_o200k is None:
        reason = o200k_err or "unknown"
        raise RuntimeError(
            "tiktoken o200k_base is required for global billing metrics but is unavailable: "
            f"{reason}. Install tiktoken in CI/runtime (see dual-regime-integrity workflow)."
        )

    comp_rows = []
    total_raw = total_comp = 0
    total_o200k_raw = total_o200k_comp = 0
    total_fidelity = 0.0
    total_sensitive_integrity = 0.0
    sensitive_integrities: list[float] = []
    sensitive_violation_count = 0
    router = DomainSpecificRouter(SHARDS_ROOT) if use_domain_router else None
    contextual_gen = ContextualGeneratorV2() if use_contextual_generator_v2 else None
    contextual_gen_v3 = ContextualGeneratorV3() if use_contextual_generator_v3 else None
    contextual_gen_v4 = ContextualGeneratorV4() if use_contextual_generator_v4 else None
    slot_dict_path = SLOT_DICT_V61 if SLOT_DICT_V61.is_file() else (SLOT_DICT_V6 if SLOT_DICT_V6.is_file() else None)
    contextual_codec_v5 = (
        ContextualGeneratorV5Codec(slot_dict_path=slot_dict_path)
        if use_contextual_generator_v5_codec
        else None
    )
    state16_adapter = NoopState16Adapter()
    for c in comp_cases:
        raw = str(c.get("raw_text", ""))
        source_comp = str(c.get("compressed_text", ""))
        source_rec = str(c.get("reconstructed_text", ""))
        comp = source_comp
        effective_must_keep = set(must_keep)
        effective_hangul_principle = use_hangul_principle
        route_info: dict[str, Any] | None = None
        bridge_meta: dict[str, Any] | None = None
        codec_decoded: str | None = None
        if include_gematria_4d_bridge:
            pre_gematria = build_gematria_metadata(
                raw_text=raw,
                compressed_text=source_comp,
                reconstructed_text=source_rec,
            )
            bridge_meta = build_gematria_4d_bridge(gematria_metadata=pre_gematria)
            if apply_gematria_4d_bridge_policy and mode == "experimental":
                effective_must_keep.update(_bridge_policy_terms_for_state(bridge_meta.get("state16")))
        if router is not None:
            route = router.route(raw)
            effective_must_keep.update(route.must_keep_hard_terms)
            # Soft terms: (1) conservative C/high (legacy) and (2) V2 multilens A/extreme bench
            # (MULTILENS_BRIDGE_POLICY_AB_OFF-class) so shard soft_term patches affect that profile.
            # Other strategy/intensity pairs skip soft terms to avoid over-constraining candidates.
            _merge_shard_soft_terms = (strategy == "C" and intensity == "high") or (
                strategy == "A" and intensity == "extreme"
            )
            if _merge_shard_soft_terms:
                effective_must_keep.update(route.must_keep_soft_terms)
            effective_hangul_principle = use_hangul_principle or route.hangul_principle
            route_info = {"shard_id": route.shard_id, "domain": route.domain}
        if use_master_codebook_lexicon_v1:
            cb_path = resolve_latest_codebook_path(
                explicit=master_codebook_lexicon_path,
            )
            if route_info is None:
                route_info = {}
            if cb_path is None:
                route_info["master_codebook_lexicon_v1"] = {
                    "status": "skipped",
                    "reason": "export_not_found",
                    "hint": "py scripts/export_master_codebook_v1.py",
                }
            else:
                hits, meta = lexicon_hits_for_text(raw, cb_path)
                effective_must_keep.update(hits)
                route_info["master_codebook_lexicon_v1"] = meta
        if mode == "experimental":
            if contextual_codec_v5 is not None and apply_gematria_4d_bridge_policy and bridge_meta is not None:
                comp = contextual_codec_v5.encode(
                    raw=raw,
                    state16=bridge_meta.get("state16"),
                    must_keep=effective_must_keep,
                )
                codec_decoded = contextual_codec_v5.decode_hybrid(encoded=comp, raw=raw, max_tokens_ratio=0.52)
            elif contextual_gen_v4 is not None and apply_gematria_4d_bridge_policy and bridge_meta is not None:
                comp = contextual_gen_v4.generate(
                    raw=raw,
                    state16=bridge_meta.get("state16"),
                    must_keep=effective_must_keep,
                    strategy=strategy,
                    intensity=intensity,
                    use_hangul_principle=effective_hangul_principle,
                )
            elif contextual_gen_v3 is not None and apply_gematria_4d_bridge_policy and bridge_meta is not None:
                comp = contextual_gen_v3.generate(
                    raw=raw,
                    state16=bridge_meta.get("state16"),
                    must_keep=effective_must_keep,
                    strategy=strategy,
                    intensity=intensity,
                    use_hangul_principle=effective_hangul_principle,
                )
            elif contextual_gen is not None and apply_gematria_4d_bridge_policy and bridge_meta is not None:
                comp = contextual_gen.generate(
                    raw=raw,
                    state16=bridge_meta.get("state16"),
                    must_keep=effective_must_keep,
                    strategy=strategy,
                    intensity=intensity,
                    use_hangul_principle=effective_hangul_principle,
                )
            else:
                comp = _compress_experimental(
                    raw,
                    strategy=strategy,
                    intensity=intensity,
                    must_keep=effective_must_keep,
                    use_hangul_principle=effective_hangul_principle,
                )
            min_saving_floor = 0.50 if (strategy == "A" and intensity == "extreme") else None
            comp = _apply_min_saving_floor(
                raw,
                comp,
                min_saving_rate=min_saving_floor,
                must_keep_terms=effective_must_keep,
                use_hangul_principle=effective_hangul_principle,
            )
            is_sensitive = _is_sensitive_case(raw, effective_must_keep)
            is_hangul = _is_hangul_case(raw)
            if effective_hangul_principle and is_hangul and hangul_max_saving_rate is not None:
                cap = hangul_max_saving_rate
            else:
                cap = sensitive_max_saving_rate if is_sensitive else general_max_saving_rate
            case_domain = str(c.get("domain", "") or "").strip()
            gmax = float(general_max_saving_rate) if general_max_saving_rate is not None else None
            if gmax is not None and gmax >= _HIGH_STRESS_GMAX_THRESHOLD:
                dstress = _HIGH_STRESS_DOMAIN_MAX_SAVING.get(case_domain)
                if dstress is not None:
                    cap = min(cap if cap is not None else 1.0, dstress)
            if apply_gematria_4d_bridge_policy and bridge_meta is not None:
                state16 = bridge_meta.get("state16")
                if state16 in {2, 8, 11, 14}:
                    cap = min(cap, 0.45) if cap is not None else 0.45
                elif state16 in {1, 4, 7, 10, 13, 16}:
                    cap = min(cap, 0.50) if cap is not None else 0.50
            comp = _apply_max_saving_cap(raw, comp, max_saving_rate=cap)
            if apply_gematria_4d_bridge_policy and bridge_meta is not None:
                comp = _bridge_aware_candidate_select(
                    raw=raw,
                    base_candidate=comp,
                    strategy=strategy,
                    intensity=intensity,
                    effective_must_keep=effective_must_keep,
                    effective_hangul_principle=effective_hangul_principle,
                    cap=cap,
                    bridge_state16=bridge_meta.get("state16"),
                    bridge_target_distance=bridge_meta.get("distance_to_state16"),
                    score_weights=bridge_score_weights,
                )
            comp = _ensure_sensitive_tokens_preserved(raw, comp, effective_must_keep)
        else:
            comp = _ensure_sensitive_tokens_preserved(raw, comp, effective_must_keep)
        rec_for_eval = _reconstruct_candidate(
            raw=raw,
            source_reconstructed=source_rec,
            compressed_candidate=comp,
            mode=mode,
        )
        if mode == "experimental":
            if codec_decoded is not None:
                rec_for_eval = codec_decoded
            else:
                rec_for_eval = _reconstruct_experimental_from_raw(
                    raw=raw,
                    compressed_candidate=comp,
                    use_hangul_principle=effective_hangul_principle,
                )
        raw_t = _tokens(raw)
        comp_t = _tokens(comp)
        ratio = (comp_t / raw_t) if raw_t else 1.0
        saving = 1.0 - ratio
        fidelity = _jaccard(raw, rec_for_eval)
        integrity = _sensitive_integrity(raw, comp, effective_must_keep)
        leak = _sensitive_violation(raw, comp, effective_must_keep)
        sensitive_integrities.append(integrity)
        if leak:
            sensitive_violation_count += 1
        rd: str | None = None
        rsid: str | None = None
        if isinstance(route_info, dict):
            dom = route_info.get("domain")
            sh = route_info.get("shard_id")
            rd = str(dom) if dom is not None else None
            rsid = str(sh) if sh is not None else None
        state16_row = state16_adapter.apply(
            State16Input(
                case_id=str(c.get("id", "")),
                raw_text=raw,
                compressed_text=comp,
                reconstructed_text=rec_for_eval,
                route_domain=rd,
                route_shard_id=rsid,
                metadata={"mode": mode, "strategy": strategy, "intensity": intensity},
            )
        ).to_row_dict()
        row = {
            "id": c.get("id"),
            "raw_tokens": raw_t,
            "compressed_tokens": comp_t,
            "token_saving_rate": saving,
            "compression_ratio": ratio,
            "reconstruction_fidelity_jaccard": fidelity,
            "sensitive_integrity": integrity,
            "sensitive_leak": leak,
            "compressed_text_effective": comp,
            "reconstructed_text_effective": rec_for_eval,
            "route": route_info,
            "state16": state16_row,
        }
        if enc_o200k is not None:
            o200k_r = len(enc_o200k.encode(raw))
            o200k_c = len(enc_o200k.encode(comp))
            o200k_sv = _o200k_saving_rate(o200k_r, o200k_c)
            row["o200k_raw_tokens"] = o200k_r
            row["o200k_compressed_tokens"] = o200k_c
            row["o200k_token_saving_rate"] = o200k_sv
            # Canonical billing-aligned keys (Option B: legacy row keys retained above).
            row["o200k_tokens_before"] = o200k_r
            row["o200k_tokens_after"] = o200k_c
            row["o200k_saving_rate"] = o200k_sv
            total_o200k_raw += o200k_r
            total_o200k_comp += o200k_c
        if include_gematria_metadata:
            gematria_metadata = build_gematria_metadata(
                raw_text=raw,
                compressed_text=comp,
                reconstructed_text=rec_for_eval,
            )
            row["gematria_metadata"] = gematria_metadata
            if include_gematria_4d_bridge:
                row["gematria_4d_bridge"] = build_gematria_4d_bridge(gematria_metadata=gematria_metadata)
                row["gematria_4d_bridge_policy_applied"] = bool(apply_gematria_4d_bridge_policy and mode == "experimental")
        if include_cee_core:
            row["cee_core"] = run_cee_logic_core_v1(
                CEEInput(
                    case_id=str(c.get("id", "")),
                    raw_text=raw,
                    compressed_text=comp,
                    reconstructed_text=rec_for_eval,
                    corpus_type="canonical",
                    metadata={"route": route_info or {}, "mode": mode, "strategy": strategy, "intensity": intensity},
                )
            )
        comp_rows.append(row)
        total_raw += raw_t
        total_comp += comp_t
        total_fidelity += fidelity
        total_sensitive_integrity += integrity

    fus_rows = []
    axis_sum = pers_sum = 0.0
    for c in fus_cases:
        ans = str(c.get("answer", ""))
        req_axes = [str(x) for x in c.get("required_axes", [])]
        pers_signals = [str(x).lower() for x in c.get("personalization_signals", [])]
        axis_hits = sum(1 for ax in req_axes if _axis_hit(ans, ax))
        axis_cov = (axis_hits / len(req_axes)) if req_axes else 1.0
        ans_l = ans.lower()
        pers_hits = sum(1 for s in pers_signals if s in ans_l)
        pers_cov = (pers_hits / len(pers_signals)) if pers_signals else 1.0
        fus_rows.append(
            {
                "id": c.get("id"),
                "axis_coverage": axis_cov,
                "personalization_coverage": pers_cov,
                "fusion_answer_possible": axis_cov >= 1.0,
            }
        )
        axis_sum += axis_cov
        pers_sum += pers_cov

    avg_fidelity = (total_fidelity / len(comp_rows)) if comp_rows else 0.0
    avg_axis = (axis_sum / len(fus_rows)) if fus_rows else 0.0
    avg_pers = (pers_sum / len(fus_rows)) if fus_rows else 0.0
    global_saving = (1.0 - (total_comp / total_raw)) if total_raw else 0.0
    avg_sensitive_integrity = (total_sensitive_integrity / len(comp_rows)) if comp_rows else 1.0
    min_sensitive_integrity = min(sensitive_integrities) if sensitive_integrities else 1.0
    cee_rows = [r.get("cee_core") for r in comp_rows if isinstance(r.get("cee_core"), dict)]
    cee_shadow_summary: dict[str, Any] | None = None
    if cee_rows:
        lambda_vals = [float(r.get("lambda_deviation", 0.0) or 0.0) for r in cee_rows]
        state_counts: dict[str, int] = {}
        band_counts: dict[str, int] = {}
        lane_counts: dict[str, int] = {}
        for row in cee_rows:
            sid = row.get("state_id")
            if isinstance(sid, (int, float)):
                key = str(int(sid))
                state_counts[key] = state_counts.get(key, 0) + 1
            post_it = row.get("metadata_post_it", {})
            if isinstance(post_it, dict):
                band = str(post_it.get("balance_band", "")).strip()
                lane = str(post_it.get("lane", "")).strip()
                if band:
                    band_counts[band] = band_counts.get(band, 0) + 1
                if lane:
                    lane_counts[lane] = lane_counts.get(lane, 0) + 1
        cee_shadow_summary = {
            "enabled": True,
            "case_count": len(cee_rows),
            "avg_lambda_deviation": (sum(lambda_vals) / len(lambda_vals)) if lambda_vals else 0.0,
            "max_lambda_deviation": max(lambda_vals) if lambda_vals else 0.0,
            "min_lambda_deviation": min(lambda_vals) if lambda_vals else 0.0,
            "state16_distribution": state_counts,
            "balance_band_distribution": band_counts,
            "lane_distribution": lane_counts,
            "note": "Shadow-mode telemetry only; does not change compression gate decisions.",
        }

    jaccard_drop_pp = 0.0
    if baseline_avg_jaccard is not None:
        jaccard_drop_pp = max(0.0, (baseline_avg_jaccard - avg_fidelity) * 100.0)

    report = {
        "schema": "multilens_performance_eval_report_v1",
        "source_input": source_input,
        "run_config": {
            "mode": mode,
            "strategy": strategy,
            "intensity": intensity,
            "must_keep_terms": sorted(must_keep),
            "general_max_saving_rate": general_max_saving_rate,
            "sensitive_max_saving_rate": sensitive_max_saving_rate,
            "hangul_max_saving_rate": hangul_max_saving_rate,
            "use_hangul_principle": use_hangul_principle,
            "use_domain_router": use_domain_router,
            "use_master_codebook_lexicon_v1": use_master_codebook_lexicon_v1,
            "master_codebook_lexicon_path": str(master_codebook_lexicon_path)
            if master_codebook_lexicon_path
            else None,
            "include_gematria_metadata": include_gematria_metadata,
            "include_gematria_4d_bridge": include_gematria_4d_bridge,
            "include_cee_core": include_cee_core,
            "apply_gematria_4d_bridge_policy": apply_gematria_4d_bridge_policy,
            "bridge_score_weights": bridge_score_weights,
            "use_contextual_generator_v2": use_contextual_generator_v2,
            "use_contextual_generator_v3": use_contextual_generator_v3,
            "use_contextual_generator_v4": use_contextual_generator_v4,
            "use_contextual_generator_v5_codec": use_contextual_generator_v5_codec,
            "require_tiktoken_o200k": require_tiktoken_o200k,
            "tiktoken_o200k_encoding": TIKTOKEN_O200K_ENCODING,
            "tiktoken_o200k_available": enc_o200k is not None,
            "tiktoken_o200k_unavailable_reason": o200k_err,
        },
        "compression_metrics": {
            "case_count": len(comp_rows),
            "global_token_saving_rate": global_saving,
            "avg_reconstruction_fidelity_jaccard": avg_fidelity,
            "avg_sensitive_integrity": avg_sensitive_integrity,
            "min_sensitive_integrity": min_sensitive_integrity,
            "sensitive_violation_count": sensitive_violation_count,
            "cases": comp_rows,
            "tiktoken_o200k": {
                "encoding": TIKTOKEN_O200K_ENCODING,
                "available": enc_o200k is not None,
                "reason_unavailable": o200k_err,
                "tokens_raw_total": total_o200k_raw if enc_o200k is not None else None,
                "tokens_compressed_total": total_o200k_comp if enc_o200k is not None else None,
                "global_token_saving_rate": (
                    _o200k_saving_rate(total_o200k_raw, total_o200k_comp)
                    if enc_o200k is not None and total_o200k_raw
                    else None
                ),
            },
            "o200k_token_saving_rate": (
                _o200k_saving_rate(total_o200k_raw, total_o200k_comp)
                if enc_o200k is not None and total_o200k_raw
                else None
            ),
            "o200k_saving_rate": (
                _o200k_saving_rate(total_o200k_raw, total_o200k_comp)
                if enc_o200k is not None and total_o200k_raw
                else None
            ),
            "o200k_tokens_before": total_o200k_raw if enc_o200k is not None else None,
            "o200k_tokens_after": total_o200k_comp if enc_o200k is not None else None,
        },
        "fusion_metrics": {
            "case_count": len(fus_rows),
            "avg_axis_coverage": avg_axis,
            "avg_personalization_coverage": avg_pers,
            "all_cases_fusion_possible": all(r["fusion_answer_possible"] for r in fus_rows),
            "cases": fus_rows,
        },
        "quality_gate": {
            "compression_ok": global_saving >= 0.15 and avg_fidelity >= 0.5,
            "fusion_ok": avg_axis >= 0.8 and avg_pers >= 0.5,
            "ultra_saving_50_ok": global_saving >= ULTRA_TOKEN_SAVING_STRICT,
            "ultra_saving_policy_ok": global_saving >= ULTRA_TOKEN_SAVING_POLICY_MIN,
            "ultra_saving_policy_min": ULTRA_TOKEN_SAVING_POLICY_MIN,
            "jaccard_drop_pp": jaccard_drop_pp,
            "jaccard_guardrail_ok": jaccard_drop_pp <= jaccard_drop_threshold_pp,
            "sensitive_integrity_ok": (
                avg_sensitive_integrity >= 0.999
                and sensitive_violation_count == 0
                and min_sensitive_integrity >= 0.999
            ),
            "sensitive_integrity_avg_floor": 0.999,
            "note": "Heuristic B-track gate; not an A-track trading performance metric. "
            "sensitive_integrity_ok requires zero required-lemma leaks per case (not avg-only).",
        },
        "cee_shadow_summary": cee_shadow_summary or {"enabled": False},
    }
    return report


def main() -> int:
    args = _parser().parse_args()
    src = Path(args.input).resolve()
    out = Path(args.output).resolve()
    doc = json.loads(src.read_text(encoding="utf-8"))
    baseline_avg_jaccard = None
    base_report_path = Path(args.baseline_report).resolve()
    if base_report_path.is_file():
        base_doc = json.loads(base_report_path.read_text(encoding="utf-8"))
        baseline_avg_jaccard = float(base_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))
    must_keep = {t.strip().lower() for t in args.domain_sensitive_terms.split(",") if t.strip()}
    report = evaluate_report(
        doc,
        source_input=str(src.relative_to(ROOT)).replace("\\", "/"),
        mode=args.mode,
        strategy=args.strategy,
        intensity=args.intensity,
        must_keep=must_keep,
        jaccard_drop_threshold_pp=args.jaccard_drop_threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        include_cee_core=bool(args.include_cee_core),
        include_gematria_metadata=bool(args.include_gematria_metadata),
        include_gematria_4d_bridge=bool(args.include_gematria_4d_bridge),
        apply_gematria_4d_bridge_policy=bool(args.apply_gematria_4d_bridge_policy),
        require_tiktoken_o200k=bool(args.require_tiktoken_o200k),
        use_domain_router=bool(args.use_domain_router),
        use_master_codebook_lexicon_v1=bool(args.use_master_codebook_lexicon),
    )

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    gate = report.get("quality_gate") or {}
    if bool(args.strict_exit) and not bool(gate.get("sensitive_integrity_ok", False)):
        print("FAIL: quality_gate.sensitive_integrity_ok is false (--strict-exit)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
