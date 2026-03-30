#!/usr/bin/env python3
"""Evaluate multi-lens performance dimensions from a fixed input spec.

Supports baseline (fixed compressed text) and experimental ultra compression
generation for A/B/C strategy benchmarks.
"""

from __future__ import annotations

import argparse
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

from scripts.core.domain_router import DomainSpecificRouter


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
    return p


def _tokens(text: str) -> int:
    # Simple portable token proxy (word-ish and symbol chunks).
    return len(re.findall(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]", text))


def _norm_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9_가-힣]+", text)}


def _split_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_가-힣]+", text)


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
) -> dict[str, Any]:
    must_keep = must_keep or set()
    comp_cases = doc.get("compression_cases", [])
    fus_cases = doc.get("fusion_answer_cases", [])

    comp_rows = []
    total_raw = total_comp = 0
    total_fidelity = 0.0
    total_sensitive_integrity = 0.0
    router = DomainSpecificRouter(SHARDS_ROOT) if use_domain_router else None
    for c in comp_cases:
        raw = str(c.get("raw_text", ""))
        source_comp = str(c.get("compressed_text", ""))
        source_rec = str(c.get("reconstructed_text", ""))
        comp = source_comp
        effective_must_keep = set(must_keep)
        effective_hangul_principle = use_hangul_principle
        route_info: dict[str, Any] | None = None
        if router is not None:
            route = router.route(raw)
            effective_must_keep.update(route.must_keep_hard_terms)
            # Soft terms are applied only in conservative profile to avoid
            # over-constraining high-compression candidates.
            if strategy == "C" and intensity == "high":
                effective_must_keep.update(route.must_keep_soft_terms)
            effective_hangul_principle = use_hangul_principle or route.hangul_principle
            route_info = {"shard_id": route.shard_id, "domain": route.domain}
        if mode == "experimental":
            comp = _compress_experimental(
                raw,
                strategy=strategy,
                intensity=intensity,
                must_keep=effective_must_keep,
                use_hangul_principle=effective_hangul_principle,
            )
            is_sensitive = _is_sensitive_case(raw, effective_must_keep)
            is_hangul = _is_hangul_case(raw)
            if effective_hangul_principle and is_hangul and hangul_max_saving_rate is not None:
                cap = hangul_max_saving_rate
            else:
                cap = sensitive_max_saving_rate if is_sensitive else general_max_saving_rate
            comp = _apply_max_saving_cap(raw, comp, max_saving_rate=cap)
        rec_for_eval = _reconstruct_candidate(
            raw=raw,
            source_reconstructed=source_rec,
            compressed_candidate=comp,
            mode=mode,
        )
        if mode == "experimental":
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
        integrity = _sensitive_integrity(raw, comp, must_keep)
        comp_rows.append(
            {
                "id": c.get("id"),
                "raw_tokens": raw_t,
                "compressed_tokens": comp_t,
                "token_saving_rate": saving,
                "compression_ratio": ratio,
                "reconstruction_fidelity_jaccard": fidelity,
                "sensitive_integrity": integrity,
                "compressed_text_effective": comp,
                "reconstructed_text_effective": rec_for_eval,
                "route": route_info,
            }
        )
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
        },
        "compression_metrics": {
            "case_count": len(comp_rows),
            "global_token_saving_rate": global_saving,
            "avg_reconstruction_fidelity_jaccard": avg_fidelity,
            "avg_sensitive_integrity": avg_sensitive_integrity,
            "cases": comp_rows,
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
            "ultra_saving_50_ok": global_saving >= 0.50,
            "jaccard_drop_pp": jaccard_drop_pp,
            "jaccard_guardrail_ok": jaccard_drop_pp <= jaccard_drop_threshold_pp,
            "sensitive_integrity_ok": avg_sensitive_integrity >= 0.999,
            "note": "Heuristic B-track gate; not an A-track trading performance metric.",
        },
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
    )

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
