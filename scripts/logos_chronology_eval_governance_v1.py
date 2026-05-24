"""Eval governance: self-match gold + human override ratio ([HYPO], disk SSOT)."""

from __future__ import annotations

from typing import Any


def assess_eval_governance(
    gold_doc: dict[str, Any],
    tag_mode: str,
    summary: dict[str, Any],
    *,
    min_human_override_ratio: float = 0.10,
    self_match_hit_threshold: float = 0.95,
) -> dict[str, Any]:
    """Downgrade status to warning when text_blind eval uses heuristic mirror gold."""
    events = list(gold_doc.get("events") or [])
    n = len(events)
    n_human = sum(1 for e in events if e.get("gold_source") == "human_override")
    n_heuristic = sum(1 for e in events if e.get("gold_source") == "heuristic_rank_top1")
    unique_golds = {str(e.get("gold_era_id")) for e in events if e.get("gold_era_id")}

    flags: list[str] = []
    status = "ok"
    ratio = (n_human / n) if n else 0.0
    hit = summary.get("hit_at_1_strict")
    schema = str(gold_doc.get("schema") or "")

    if tag_mode == "text_blind" and n > 0:
        if n_heuristic > 0 and ratio < min_human_override_ratio:
            flags.append("SELF_MATCH_GOLD_NO_HUMAN_OVERRIDE")
        if schema == "logos_chronology_hardset_news_era_gold_v1" and n_human == 0:
            flags.append("LEGACY_UNIFORM_MODERN_GOLD")
        if len(unique_golds) == 1:
            flags.append("SINGLE_ERA_GOLD_SKEW")
        if hit is not None and float(hit) >= self_match_hit_threshold and n_human == 0:
            flags.append("SUSPICIOUS_PERFECT_HIT_NO_HUMAN_GOLD")
        if flags:
            status = "warning"

    limitation_lines = []
    if "SELF_MATCH_GOLD_NO_HUMAN_OVERRIDE" in flags:
        limitation_lines.append(
            "Gold includes heuristic_rank_top1 with human_override ratio below threshold; "
            "hit rate is pipeline self-match smoke, not external validation."
        )
    if "LEGACY_UNIFORM_MODERN_GOLD" in flags:
        limitation_lines.append("Hardset v1 uniform modern gold: high hit@1 may reflect label skew only.")
    if "SINGLE_ERA_GOLD_SKEW" in flags:
        limitation_lines.append("All events share one gold_era_id; text_blind metrics are not discriminative.")
    if "SUSPICIOUS_PERFECT_HIT_NO_HUMAN_GOLD" in flags:
        limitation_lines.append(
            f"hit_at_1_strict>={self_match_hit_threshold} with zero human_override rows — do not cite as accuracy."
        )

    return {
        "governance_schema": "logos_chronology_eval_governance_v1",
        "status": status,
        "flags": flags,
        "n_events": n,
        "n_human_override": n_human,
        "n_heuristic_rank_top1": n_heuristic,
        "human_override_ratio": round(ratio, 6) if n else None,
        "min_human_override_ratio": min_human_override_ratio,
        "unique_gold_era_count": len(unique_golds),
        "limitation_lines": limitation_lines,
        "interpretation_ko": (
            "text_blind + heuristic gold without human rows = mirror eval only. "
            "MS/public: cite 4.3% historical text_blind only."
        ),
    }
