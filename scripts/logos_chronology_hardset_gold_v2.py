#!/usr/bin/env python3
"""Hardset era gold strategies: uniform_modern | rank_top1 | overrides merge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from logos_chronology_map_core_v1 import infer_tags_from_text, load_json, rank_eras

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"


def rank_top1_era_id(
    chrono: dict[str, Any],
    text: str,
    *,
    modern_boost: float = 0.08,
    boost_policy: str = "tier_v1",
) -> tuple[str, list[str], list[dict[str, Any]]]:
    tags = infer_tags_from_text(text)
    ranking = rank_eras(
        chrono,
        tags,
        modern_boost=modern_boost,
        event_tier="news_hardset",
        boost_policy=boost_policy,
    )
    gold = str(ranking[0]["era_id"]) if ranking else "modern_observational_field"
    return gold, tags, ranking[:3]


def apply_overrides(events: list[dict[str, Any]], overrides: dict[str, Any]) -> list[dict[str, Any]]:
    by_obs: dict[str, dict[str, Any]] = {
        str(o.get("observation_id")): o for o in (overrides.get("overrides") or []) if o.get("observation_id")
    }
    out: list[dict[str, Any]] = []
    for ev in events:
        row = dict(ev)
        oid = str(ev.get("observation_id") or "")
        if oid in by_obs:
            o = by_obs[oid]
            if o.get("gold_era_id"):
                row["gold_era_id"] = o["gold_era_id"]
            if o.get("acceptable_era_ids"):
                row["acceptable_era_ids"] = o["acceptable_era_ids"]
            row["gold_source"] = "human_override"
            row["gold_rationale_ko"] = str(o.get("rationale_ko") or row.get("gold_rationale_ko") or "")
        out.append(row)
    return out
