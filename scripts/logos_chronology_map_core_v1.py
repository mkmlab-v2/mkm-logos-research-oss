"""Shared chronology era ranking core ([HYPO], NON_GATING). Used by dynamic map builder and blind eval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POLICY = {
    "research_only": True,
    "non_gating": True,
    "no_trading_signal": True,
}

REGIME_ID_HINTS: dict[str, list[str]] = {
    "post_covid_normalization": ["covid", "risk"],
    "pandemic_shock": ["covid", "risk"],
    "post_gfc_repair": ["imf", "stability"],
    "lehman": ["lehman", "risk"],
    "imf": ["imf", "risk"],
    "it_bubble": ["it_bubble", "risk"],
    "covid": ["covid", "risk"],
    "elevated": ["risk", "lehman"],
    "watch": ["risk", "caution"],
    "caution": ["caution", "risk"],
    "stability": ["stability"],
    "empire_transition": ["empire_transition", "it_bubble"],
}

# Text keyword -> regime_map-style tags (observational only).
TEXT_TAG_KEYWORDS: list[tuple[str, str]] = [
    ("lehman", "lehman"),
    ("subprime", "lehman"),
    ("credit spread", "lehman"),
    ("credit spreads widen", "lehman"),
    ("bank run", "lehman"),
    ("covid", "covid"),
    ("pandemic", "covid"),
    ("lockdown", "covid"),
    ("imf", "imf"),
    ("asian financial", "imf"),
    ("currency crisis", "imf"),
    ("dot-com", "it_bubble"),
    ("dotcom", "it_bubble"),
    ("tech bubble", "it_bubble"),
    ("nasdaq", "it_bubble"),
    ("volatility rises", "risk"),
    ("risk-off", "risk"),
    ("geopolitical", "risk"),
    ("liquidity thin", "lehman"),
    ("rate hike", "risk"),
    ("tightening", "risk"),
    ("inflation surge", "risk"),
    ("recession", "risk"),
    ("covenant", "stability"),
    ("patriarch", "stability"),
    ("exodus", "empire_transition"),
    ("babylon", "empire_transition"),
    ("exile", "imf"),
    ("return from exile", "imf"),
    ("gospel", "stability"),
    ("resurrection", "stability"),
    ("early church", "stability"),
    ("acts ", "stability"),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def infer_tags_from_macro(macro: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    snap = macro.get("market_snapshot") or {}
    rid = str(snap.get("primary_regime_id") or "").strip().lower()
    if rid:
        tags.update(REGIME_ID_HINTS.get(rid, [rid.replace("-", "_")]))
    level = str(snap.get("risk_warning_level") or "").strip().lower()
    if level:
        tags.update(REGIME_ID_HINTS.get(level, ["risk"]))
    state = str(snap.get("decision_state") or "").strip().lower()
    if state:
        tags.update(REGIME_ID_HINTS.get(state, []))
    for sig in macro.get("top_risk_signals") or []:
        if not isinstance(sig, dict):
            continue
        name = str(sig.get("name") or "").lower()
        if "volatility" in name or "stress" in name or "tail" in name:
            tags.add("risk")
        if "liquidity" in name:
            tags.add("lehman")
    return sorted(tags)


def infer_tags_from_text(text: str) -> list[str]:
    low = (text or "").lower()
    tags: set[str] = set()
    for needle, tag in TEXT_TAG_KEYWORDS:
        if needle in low:
            tags.add(tag)
    return sorted(tags)


def era_rows(chrono: dict[str, Any]) -> list[dict[str, Any]]:
    eras = chrono.get("eras") or []
    bridges = chrono.get("modern_bridges") or []
    bridge_by_era: dict[str, list[dict[str, Any]]] = {}
    for b in bridges:
        if isinstance(b, dict):
            bridge_by_era.setdefault(str(b.get("era_id") or ""), []).append(b)
    rows: list[dict[str, Any]] = []
    for e in eras:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("era_id") or "")
        obs = [str(t) for t in (e.get("regime_tags_observational") or [])]
        rows.append(
            {
                "era_id": eid,
                "label_ko": str(e.get("label_ko") or eid),
                "obs_tags": obs,
                "bridges": bridge_by_era.get(eid, []),
            }
        )
    return rows


def score_era(row: dict[str, Any], inferred: set[str]) -> tuple[float, list[str], int]:
    obs = set(row.get("obs_tags") or [])
    matched = sorted(obs & inferred)
    tag_score = (len(matched) / max(len(inferred), 1)) if inferred else 0.0
    bridge_hits = 0
    for b in row.get("bridges") or []:
        rid = str(b.get("regime_id") or "").strip()
        if rid and rid in inferred:
            bridge_hits += 1
        w = b.get("resonance_weight")
        try:
            bw = float(w) if w is not None else 1.0
        except (TypeError, ValueError):
            bw = 1.0
        if bridge_hits and rid in inferred:
            tag_score = min(1.0, tag_score + 0.05 * bw)
    raw = 0.65 * tag_score + 0.35 * min(1.0, bridge_hits / 3.0)
    return round(min(1.0, raw), 6), matched, bridge_hits


NARRATIVE_TIERS = frozenset({"biblical_narrative"})
LOCKED_EVAL_PARTITION = "locked_eval"
JUDGES_ERA = "judges_risk_cycle"
MODERN_ERA = "modern_observational_field"
TIER_V2_POLICIES = frozenset({"tier_v2_locked_eval"})


def _locked_eval_risk_cluster(inferred: set[str]) -> bool:
    return bool({"risk"} & inferred) and bool({"lehman", "caution"} & inferred)


def resolve_modern_boost(
    event_tier: str | None,
    modern_boost: float,
    boost_policy: str,
) -> float:
    """tier_v1: no modern boost on narrative tier (배선 오염 차단).

    tier_v2_locked_eval: tier_v1 + locked_eval risk-cluster rows block modern boost bleed.
    """
    if boost_policy in ("tier_v1", *TIER_V2_POLICIES) and event_tier in NARRATIVE_TIERS:
        return 0.0
    return modern_boost


def apply_locked_eval_score_adjustments(
    era_id: str,
    score: float,
    inferred: set[str],
    *,
    event_partition: str | None,
    boost_policy: str,
) -> float:
    """Dampen modern overlap; lift judges when locked_eval carries risk+lehman/caution tags."""
    if boost_policy not in TIER_V2_POLICIES:
        return score
    if event_partition != LOCKED_EVAL_PARTITION or not _locked_eval_risk_cluster(inferred):
        return score
    if era_id == MODERN_ERA:
        return max(0.0, round(score - 0.20, 6))
    if era_id == JUDGES_ERA:
        return min(1.0, round(score + 0.16, 6))
    return score


def rank_eras(
    chrono: dict[str, Any],
    inferred_tags: list[str],
    *,
    modern_boost: float = 0.0,
    event_tier: str | None = None,
    event_partition: str | None = None,
    boost_policy: str = "global",
) -> list[dict[str, Any]]:
    inferred_set = set(inferred_tags)
    effective_boost = resolve_modern_boost(event_tier, modern_boost, boost_policy)
    if boost_policy in TIER_V2_POLICIES and event_partition == LOCKED_EVAL_PARTITION:
        if _locked_eval_risk_cluster(inferred_set):
            effective_boost = 0.0
    ranking: list[dict[str, Any]] = []
    for row in era_rows(chrono):
        score, matched, bh = score_era(row, inferred_set)
        if row["era_id"] == MODERN_ERA and inferred_set:
            score = min(1.0, score + effective_boost)
        score = apply_locked_eval_score_adjustments(
            str(row["era_id"]),
            score,
            inferred_set,
            event_partition=event_partition,
            boost_policy=boost_policy,
        )
        ranking.append(
            {
                "era_id": row["era_id"],
                "label_ko": row["label_ko"],
                "score": score,
                "matched_tags": matched,
                "matched_bridges": bh,
                "interpretation_class": "[HYPO]",
            }
        )
    ranking.sort(key=lambda r: (-float(r["score"]), str(r["era_id"])))
    return ranking


def confidence_band(score: float) -> str:
    if score >= 0.55:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"
