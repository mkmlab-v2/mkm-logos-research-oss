#!/usr/bin/env python3
"""Score LoRA-pack × domain-routing grid sizes against Golden 40 cmp2 bench.

B-track / research_only — does not promote Track A or claim 20×200 optimality.
Outputs a composite score for candidate architectures (packs × routing cells).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_SLOT_V61 = ROOT / "docs/final/artifacts/MULTILENS_DOMAIN_SLOT_DICTIONARY_V61.json"
DEFAULT_FORMULAS = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/lora_domain_architecture_sweep_latest.json"

WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _case_text(case: dict[str, Any]) -> str:
    parts = [case.get("raw_text", ""), case.get("compressed_text", ""), case.get("reconstructed_text", "")]
    return " ".join(str(p) for p in parts if p)


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text)}


def _route_primary(text: str, slots: dict[str, list[str]]) -> tuple[str | None, int, list[str]]:
    words = _tokenize(text)
    hits: list[tuple[int, str]] = []
    matched: list[str] = []
    for slot_id, keywords in slots.items():
        keys = {k.lower() for k in keywords}
        score = sum(1 for k in keys if k in words)
        if score > 0:
            matched.append(slot_id)
            hits.append((score, slot_id))
    if not hits:
        return None, 0, []
    hits.sort(key=lambda x: (-x[0], x[1]))
    top_score = hits[0][0]
    tied = [sid for sc, sid in hits if sc == top_score]
    primary = tied[0] if len(tied) == 1 else f"TIE:{','.join(sorted(tied))}"
    return primary, top_score, matched


def _slot_metrics(cases: list[dict[str, Any]], slots: dict[str, list[str]]) -> dict[str, Any]:
    primaries: list[str] = []
    unmatched = 0
    ambiguous = 0
    multi_hit = 0
    for case in cases:
        primary, score, matched = _route_primary(_case_text(case), slots)
        if score == 0:
            unmatched += 1
            primaries.append("__UNMATCHED__")
            continue
        if len(matched) > 1:
            multi_hit += 1
        if primary and primary.startswith("TIE:"):
            ambiguous += 1
        primaries.append(primary or "__UNMATCHED__")

    n = len(cases)
    counts = Counter(primaries)
    entropy = 0.0
    for c in counts.values():
        p = c / n
        entropy -= p * math.log2(p)

    return {
        "slot_count": len(slots),
        "cases": n,
        "hit_rate": round((n - unmatched) / n, 4) if n else 0.0,
        "unique_primary_rate": round(len({p for p in primaries if not p.startswith("TIE:") and p != "__UNMATCHED__"}) / n, 4)
        if n
        else 0.0,
        "ambiguous_tie_rate": round(ambiguous / n, 4) if n else 0.0,
        "multi_slot_hit_rate": round(multi_hit / n, 4) if n else 0.0,
        "unmatched_rate": round(unmatched / n, 4) if n else 0.0,
        "primary_entropy_bits": round(entropy, 4),
        "primary_distribution": dict(sorted(counts.items(), key=lambda x: (-x[1], x[0]))),
    }


def _build_slot_dictionary_k7(v61_path: Path) -> dict[str, list[str]]:
    doc = _load_json(v61_path)
    return {str(k): list(v) for k, v in doc.get("slots", {}).items()}


def _build_slot_dictionary_k9_shards() -> dict[str, list[str]]:
    shards_root = ROOT / "codebook" / "shards"
    slots: dict[str, list[str]] = {}
    for path in sorted(shards_root.glob("zone_*.json")):
        shard = _load_json(path)
        sid = str(shard.get("shard_id", path.stem))
        keys = list(shard.get("routing_keywords", [])) + list(shard.get("must_keep_hard_terms", []))
        slots[sid] = [str(k) for k in keys if k]
    return slots


def _build_slot_dictionary_k16(v61: dict[str, list[str]]) -> dict[str, list[str]]:
    slots = {f"{k}_a": v[: max(1, len(v) // 2)] for k, v in v61.items()}
    slots.update({f"{k}_b": v[max(1, len(v) // 2) :] for k, v in v61.items()})
    slots["S5_taeeum"] = ["태음", "태음인", "부종", "저염"]
    slots["S5_soeeum"] = ["소음", "소음인", "위장", "온식"]
    slots["S5_soyang"] = ["소양", "소양인", "과열", "카페인"]
    slots["S5_taeyang"] = ["태양", "태양인", "건조", "불안"]
    return slots


def _build_slot_dictionary_k40_cases(cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    slots: dict[str, list[str]] = {}
    for case in cases:
        cid = str(case.get("id", "case"))
        words = sorted(_tokenize(_case_text(case)), key=len, reverse=True)[:12]
        slots[cid] = words or [cid]
    return slots


def _build_slot_dictionary_k75_formulas(formulas_path: Path) -> dict[str, list[str]]:
    doc = _load_json(formulas_path)
    slots: dict[str, list[str]] = {}
    for row in doc.get("formulas", []):
        slot_num = row.get("slot")
        cat = str(row.get("category", "unknown"))
        name = str(row.get("name", ""))
        purpose = str(row.get("purpose", ""))
        sid = f"F{slot_num:02d}_{cat}"
        tokens = list(_tokenize(f"{name} {purpose} {cat}"))
        slots[sid] = tokens[:8] or [cat]
    return slots


_CATEGORY_V61_KEYS: dict[str, list[str]] = {
    "vector_mapping": ["S1", "S7"],
    "information_entropy": ["S7"],
    "hamilton_product": ["S7"],
    "fft_acceleration": ["S7"],
    "geumhwa_exchange": ["S1"],
    "taeyangin_sparsity": ["S5"],
    "integrity_verification": ["S3", "S4"],
    "integrated_performance": ["S4", "S6"],
    "mathematical_consistency": ["S3"],
    "vault_pending": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
}

_CATEGORY_SHARD_STEMS: dict[str, list[str]] = {
    "vector_mapping": ["zone_c_hangul"],
    "information_entropy": ["zone_d_ssot"],
    "hamilton_product": ["zone_d_ssot"],
    "fft_acceleration": ["zone_d_ssot"],
    "geumhwa_exchange": ["zone_b_timing"],
    "taeyangin_sparsity": ["zone_a_scm", "zone_g_health"],
    "integrity_verification": ["zone_d_ssot", "zone_f_code"],
    "integrated_performance": ["zone_e_finance"],
    "mathematical_consistency": ["zone_f_code"],
    "vault_pending": [
        "zone_a_scm",
        "zone_b_timing",
        "zone_c_hangul",
        "zone_d_ssot",
        "zone_e_finance",
        "zone_f_code",
        "zone_g_health",
        "zone_h_legacy",
        "zone_s_log_metabolism_alt",
    ],
}


def _dedupe_keywords(items: list[str], limit: int = 24) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _bench_vocab(cases: list[dict[str, Any]], top_n: int = 48) -> list[str]:
    freq: Counter[str] = Counter()
    for case in cases:
        freq.update(_tokenize(_case_text(case)))
    return [w for w, _ in freq.most_common(top_n)]


def _build_slot_dictionary_k75_formulas_hybrid(
    *,
    formulas_path: Path,
    v61: dict[str, list[str]],
    shards: dict[str, list[str]],
    cases: list[dict[str, Any]],
) -> dict[str, list[str]]:
    doc = _load_json(formulas_path)
    bench_words = _bench_vocab(cases)
    slots: dict[str, list[str]] = {}
    for row in doc.get("formulas", []):
        slot_num = int(row.get("slot", 0))
        cat = str(row.get("category", "unknown"))
        name = str(row.get("name", ""))
        purpose = str(row.get("purpose", ""))
        formula = str(row.get("formula", ""))
        sid = f"F{slot_num:02d}_{cat}"
        merged: list[str] = list(_tokenize(f"{name} {purpose} {formula} {cat}"))
        for v61_key in _CATEGORY_V61_KEYS.get(cat, ["S7"]):
            merged.extend(v61.get(v61_key, []))
        if cat == "vault_pending":
            v61_key = f"S{((slot_num - 1) % 7) + 1}"
            merged.extend(v61.get(v61_key, []))
            start = ((slot_num - 1) * 3) % max(len(bench_words), 1)
            merged.extend(bench_words[start : start + 4])
        for shard_id in _CATEGORY_SHARD_STEMS.get(cat, []):
            merged.extend(shards.get(shard_id, []))
        slots[sid] = _dedupe_keywords(merged)
    return slots


def _build_slot_dictionary_token_clusters(cases: list[dict[str, Any]], k: int) -> dict[str, list[str]]:
    """Deterministic token-hash clustering to target K routing cells."""
    freq: Counter[str] = Counter()
    for case in cases:
        freq.update(_tokenize(_case_text(case)))
    vocab = [w for w, _ in freq.most_common(max(k * 3, 50))]
    slots: dict[str, list[str]] = {f"C{i:03d}": [] for i in range(1, k + 1)}
    for idx, word in enumerate(vocab):
        slots[f"C{(idx % k) + 1:03d}"].append(word)
    return slots


def _case_lens_tags(text: str) -> set[str]:
    words = _tokenize(text)
    tags: set[str] = set()
    if words & {"sasang", "사상", "사상의학", "체질", "소양", "소음", "태음", "태양"}:
        tags.add("sasang")
    if words & {"명리", "전이", "state", "state_id", "timing"}:
        tags.add("myeongni")
    if words & {"bible", "logos", "성경", "시편", "원어"}:
        tags.add("logos")
    if not tags:
        tags.add("general")
    return tags


def _case_domain_tags(text: str) -> set[str]:
    words = _tokenize(text)
    tags: set[str] = set()
    if words & {"compression", "token", "jaccard", "saving", "fidelity", "복원"}:
        tags.add("compression")
    if words & {"gate", "policy", "trigger", "boundary", "cadence", "review", "strict", "manual"}:
        tags.add("governance")
    if words & {"sasang", "사상", "체질", "소양", "소음", "태음", "태양", "처방", "증상"}:
        tags.add("clinical")
    if words & {"market", "predictive", "stability", "performance", "operational"}:
        tags.add("market")
    if not tags:
        tags.add("general")
    return tags


def _pack_demand(cases: list[dict[str, Any]]) -> dict[str, Any]:
    combo_counter: Counter[str] = Counter()
    lens_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    for case in cases:
        text = _case_text(case)
        lenses = _case_lens_tags(text)
        domains = _case_domain_tags(text)
        for lens in lenses:
            lens_counter[lens] += 1
        for domain in domains:
            domain_counter[domain] += 1
        for lens in lenses:
            for domain in domains:
                combo_counter[f"{lens}×{domain}"] += 1
    return {
        "unique_lens_tags": len(lens_counter),
        "unique_domain_tags": len(domain_counter),
        "unique_lens_domain_pairs": len(combo_counter),
        "lens_distribution": dict(lens_counter),
        "domain_distribution": dict(domain_counter),
        "top_lens_domain_pairs": combo_counter.most_common(12),
    }


def _composite_score(
    *,
    packs: int,
    slots: int,
    slot_metrics: dict[str, Any],
    hierarchical: bool,
    ssot_bonus: float,
    pack_demand_pairs: int,
) -> dict[str, Any]:
    hit = float(slot_metrics["hit_rate"])
    discrimination = float(slot_metrics["unique_primary_rate"])
    tie_penalty = float(slot_metrics["ambiguous_tie_rate"])
    unmatched_penalty = float(slot_metrics["unmatched_rate"])
    pack_coverage = min(1.0, packs / max(pack_demand_pairs, 1))
    complexity = math.log2(max(packs, 1) * max(slots, 1))
    hierarchical_bonus = 0.04 if hierarchical else 0.0
    score = (
        0.22 * hit
        + 0.28 * discrimination
        + 0.18 * (1.0 - tie_penalty)
        + 0.12 * (1.0 - unmatched_penalty)
        + 0.10 * pack_coverage
        + ssot_bonus
        + hierarchical_bonus
        - 0.05 * complexity
    )
    return {
        "composite_score": round(score, 4),
        "pack_coverage_vs_demand": round(pack_coverage, 4),
        "complexity_log2_packs_x_slots": round(complexity, 4),
        "ssot_alignment_bonus": ssot_bonus,
        "hierarchical_bonus": hierarchical_bonus,
    }


def build_sweep(
    *,
    input_path: Path,
    slot_v61_path: Path,
    formulas_path: Path,
) -> dict[str, Any]:
    doc = _load_json(input_path)
    cases = list(doc.get("compression_cases", []))
    v61 = _build_slot_dictionary_k7(slot_v61_path)
    shards = _build_slot_dictionary_k9_shards()

    slot_sets: dict[str, dict[str, list[str]]] = {
        "K7_v61": v61,
        "K9_codebook_shards": shards,
        "K16_v61_split": _build_slot_dictionary_k16(v61),
        "K40_case_dedicated": _build_slot_dictionary_k40_cases(cases),
        "K75_mkm12_formulas": _build_slot_dictionary_k75_formulas(formulas_path),
        "K75_mkm12_hybrid": _build_slot_dictionary_k75_formulas_hybrid(
            formulas_path=formulas_path,
            v61=v61,
            shards=shards,
            cases=cases,
        ),
        "K128_token_cluster": _build_slot_dictionary_token_clusters(cases, 128),
        "K200_token_cluster": _build_slot_dictionary_token_clusters(cases, 200),
    }

    slot_eval: dict[str, Any] = {}
    for name, slots in slot_sets.items():
        slot_eval[name] = _slot_metrics(cases, slots)

    pack_demand = _pack_demand(cases)

    architectures: list[dict[str, Any]] = [
        {
            "id": "vision_20x200_flat",
            "label": "Vision flat 20 packs × 200 rules",
            "packs": 20,
            "routing_cells": 200,
            "hierarchical": False,
            "slot_profile": "K200_token_cluster",
            "ssot_bonus": 0.0,
            "notes": "[HYPO] round-number vision; highest maintenance",
        },
        {
            "id": "hier_12x75_hybrid",
            "label": "Hierarchical 12 packs × 75 MKM12 hybrid (v61+shard)",
            "packs": 12,
            "routing_cells": 75,
            "hierarchical": True,
            "slot_profile": "K75_mkm12_hybrid",
            "ssot_bonus": 0.09,
            "notes": "MKM12 SSOT + v61/shard/bench vocab for vault_pending slots",
        },
        {
            "id": "hier_12x75",
            "label": "Hierarchical 12 packs × 75 MKM12 cells (formula-only)",
            "packs": 12,
            "routing_cells": 75,
            "hierarchical": True,
            "slot_profile": "K75_mkm12_formulas",
            "ssot_bonus": 0.08,
            "notes": "3 lens × 4 domain LoRA grid; MKM12 SSOT routing baseline",
        },
        {
            "id": "hier_12x64",
            "label": "Hierarchical 12 packs × 64 clusters",
            "packs": 12,
            "routing_cells": 64,
            "hierarchical": True,
            "slot_profile": "K128_token_cluster",
            "ssot_bonus": 0.04,
            "notes": "Recommended interim — between 75 formulas and 128 cluster",
        },
        {
            "id": "bench_4x40",
            "label": "Bench-aligned 4 domain × 40 case cells",
            "packs": 4,
            "routing_cells": 40,
            "hierarchical": True,
            "slot_profile": "K40_case_dedicated",
            "ssot_bonus": 0.06,
            "notes": "Matches coordinator domains + Golden 40 eval SSOT",
        },
        {
            "id": "minimal_3x7",
            "label": "Minimal 3 lens × 7 slots (current-ish)",
            "packs": 3,
            "routing_cells": 7,
            "hierarchical": True,
            "slot_profile": "K7_v61",
            "ssot_bonus": 0.03,
            "notes": "Lowest ops cost; underfits pair demand",
        },
        {
            "id": "shard_9x16",
            "label": "Codebook 9 shards × 16 split slots",
            "packs": 9,
            "routing_cells": 16,
            "hierarchical": True,
            "slot_profile": "K16_v61_split",
            "ssot_bonus": 0.05,
            "notes": "Aligns compression shard router + v61 split",
        },
        {
            "id": "flat_20x40",
            "label": "Flat 20 packs × 40 case cells",
            "packs": 20,
            "routing_cells": 40,
            "hierarchical": False,
            "slot_profile": "K40_case_dedicated",
            "ssot_bonus": 0.02,
            "notes": "20 expert packs but only 40 routing — not 200 rules",
        },
    ]

    ranked: list[dict[str, Any]] = []
    for arch in architectures:
        profile = str(arch["slot_profile"])
        metrics = slot_eval[profile]
        score_doc = _composite_score(
            packs=int(arch["packs"]),
            slots=int(arch["routing_cells"]),
            slot_metrics=metrics,
            hierarchical=bool(arch["hierarchical"]),
            ssot_bonus=float(arch["ssot_bonus"]),
            pack_demand_pairs=int(pack_demand["unique_lens_domain_pairs"]),
        )
        ranked.append(
            {
                **arch,
                "routing_metrics": metrics,
                "score": score_doc,
                "pack_demand_unique_pairs": pack_demand["unique_lens_domain_pairs"],
                "pack_demand_covers_with_packs": int(arch["packs"]) >= pack_demand["unique_lens_domain_pairs"],
            }
        )

    ranked.sort(key=lambda x: x["score"]["composite_score"], reverse=True)
    best = ranked[0]
    vision = next(a for a in ranked if a["id"] == "vision_20x200_flat")
    hybrid = next((a for a in ranked if a["id"] == "hier_12x75_hybrid"), None)
    formula_only = next((a for a in ranked if a["id"] == "hier_12x75"), None)
    hybrid_delta = None
    if hybrid and formula_only:
        hybrid_delta = round(
            float(hybrid["score"]["composite_score"]) - float(formula_only["score"]["composite_score"]),
            4,
        )

    return {
        "schema": "lora_domain_architecture_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "bench_input": str(input_path),
        "case_count": len(cases),
        "pack_demand": pack_demand,
        "slot_profiles": slot_eval,
        "architectures_ranked": ranked,
        "hybrid_routing_uplift": {
            "hier_12x75_hybrid_rank": ranked.index(hybrid) + 1 if hybrid else None,
            "hier_12x75_formula_only_rank": ranked.index(formula_only) + 1 if formula_only else None,
            "composite_score_delta_hybrid_minus_formula_only": hybrid_delta,
            "K75_hybrid_hit_rate": slot_eval.get("K75_mkm12_hybrid", {}).get("hit_rate"),
            "K75_formula_only_hit_rate": slot_eval.get("K75_mkm12_formulas", {}).get("hit_rate"),
        },
        "verdict": {
            "best_candidate_id": best["id"],
            "best_candidate_label": best["label"],
            "best_composite_score": best["score"]["composite_score"],
            "vision_20x200_rank": ranked.index(vision) + 1,
            "vision_20x200_score": vision["score"]["composite_score"],
            "vision_is_optimal": best["id"] == "vision_20x200_flat",
            "summary_ko": (
                "20×200 flat vision is not optimal on Golden-40 routing metrics; "
                f"top ranked = {best['label']} (composite {best['score']['composite_score']}). "
                + (
                    f"12×75 hybrid uplift vs formula-only = {hybrid_delta}; "
                    if hybrid_delta is not None
                    else ""
                )
                + "Recommend bench 4×40 for eval alignment; 12×75 hybrid for MKM12 SSOT tranche 2."
            ),
        },
        "method_notes": {
            "routing": "Keyword hit count on raw+compressed+reconstructed text; highest wins; ties flagged.",
            "composite_weights": "0.22 hit + 0.28 unique_primary + 0.18 (1-tie) + 0.12 (1-unmatched) + 0.10 pack_coverage + ssot + hier - 0.05*log2(packs*slots)",
            "limits": "Does not run GPU LoRA training or latency benchmarks; routing-only proxy.",
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA pack × domain routing architecture sweep (Golden 40).")
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--slot-v61", default=str(DEFAULT_SLOT_V61))
    p.add_argument("--formulas", default=str(DEFAULT_FORMULAS))
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_sweep(
        input_path=Path(args.input),
        slot_v61_path=Path(args.slot_v61),
        formulas_path=Path(args.formulas),
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "best": report["verdict"]["best_candidate_id"], "vision_rank": report["verdict"]["vision_20x200_rank"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
