#!/usr/bin/env python3
"""Build off-fixture era gold: hardset v2 + blind_split OOV expansion (disjoint from historical 47)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logos_chronology_hardset_gold_v2 import apply_overrides, rank_top1_era_id
from logos_chronology_map_core_v1 import load_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HIST_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_HARDSET_GOLD = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_BLIND_SPLIT = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_latest.jsonl"
DEFAULT_EXPANSION_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_HARDSET_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
DEFAULT_CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_OVERRIDES = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_era_gold_v1_latest.json"
EXCLUDED_SOURCES = frozenset({"label_guided_seed", "manual_seed"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _token_set(text: str) -> set[str]:
    return {t.strip(".,!?;:\"'()[]{}").lower() for t in text.split() if t.strip()}


def _hard_filter(row: dict[str, Any], *, min_words: int) -> bool:
    text = str(row.get("canonical_text") or "")
    words = text.split()
    uniq = _token_set(text)
    return len(words) >= min_words and len(uniq) >= 8


def _event_from_news_row(
    row: dict[str, Any],
    chrono: dict[str, Any],
    *,
    modern_boost: float,
    boost_policy: str,
    event_id_prefix: str,
    tier: str,
) -> dict[str, Any]:
    text = str(row.get("canonical_text") or "")
    gold, tags, top3 = rank_top1_era_id(
        chrono,
        text,
        modern_boost=modern_boost,
        boost_policy=boost_policy,
    )
    oid = str(row.get("observation_id") or "")
    return {
        "event_id": f"{event_id_prefix}{oid}",
        "tier": tier,
        "as_of_date": str(row.get("as_of_utc") or "")[:10],
        "partition": row.get("dataset_partition") or "train_holdout",
        "observation_id": oid,
        "source_id": row.get("source_id"),
        "canonical_text": text,
        "headline_ko": text[:160],
        "inferred_regime_tags_operator": tags,
        "gold_era_id": gold,
        "acceptable_era_ids": [gold, "modern_observational_field", "judges_risk_cycle"],
        "gold_source": "heuristic_rank_top1",
        "gold_rationale_ko": (
            "live news OOV expansion + rank_top1 (tier_v1). "
            "Not human-labeled unless override; B-track off-fixture only."
        ),
        "heuristic_top3_era_ids": [r["era_id"] for r in top3],
        "is_synthetic_source": False,
        "cohort": "off_fixture_oov_expansion",
    }


def build_off_fixture_gold(
    *,
    hist_gold_path: Path,
    hardset_gold_path: Path,
    blind_split_path: Path,
    expansion_news_path: Path,
    hardset_news_path: Path,
    chrono_path: Path,
    overrides_path: Path,
    modern_boost: float,
    boost_policy: str,
    max_expansion_rows: int,
    min_words: int,
) -> dict[str, Any]:
    hist_doc = load_json(hist_gold_path)
    hist_ids = {str(e.get("event_id")) for e in (hist_doc.get("events") or []) if e.get("event_id")}

    if hardset_gold_path.is_file():
        hardset_doc = load_json(hardset_gold_path)
        events: list[dict[str, Any]] = []
        for ev in hardset_doc.get("events") or []:
            row = dict(ev)
            row["cohort"] = "off_fixture_hardset_v2"
            row["event_id"] = str(row.get("event_id") or "")
            events.append(row)
    else:
        events = []

    hardset_obs = {str(e.get("observation_id")) for e in events if e.get("observation_id")}
    if hardset_news_path.is_file():
        for row in _load_jsonl(hardset_news_path):
            oid = str(row.get("observation_id") or "")
            if oid:
                hardset_obs.add(oid)

    chrono = load_json(chrono_path)
    expansion: list[dict[str, Any]] = []
    seen_sha: set[str] = set()
    expansion_sources: list[Path] = []
    if blind_split_path.is_file():
        expansion_sources.append(blind_split_path)
    if expansion_news_path.is_file() and expansion_news_path != blind_split_path:
        expansion_sources.append(expansion_news_path)

    if max_expansion_rows > 0:
        for src_path in expansion_sources:
            for row in _load_jsonl(src_path):
                oid = str(row.get("observation_id") or "")
                sid = str(row.get("source_id") or "")
                sha = str(row.get("text_sha256") or "")
                if not oid or oid in hardset_obs or sid in EXCLUDED_SOURCES:
                    continue
                if sha and sha in seen_sha:
                    continue
                if not _hard_filter(row, min_words=min_words):
                    continue
                seen_sha.add(sha)
                expansion.append(
                    _event_from_news_row(
                        row,
                        chrono,
                        modern_boost=modern_boost,
                        boost_policy=boost_policy,
                        event_id_prefix="off-fixture-",
                        tier="news_off_fixture",
                    )
                )
                if len(expansion) >= max_expansion_rows:
                    break
            if len(expansion) >= max_expansion_rows:
                break
        expansion.sort(key=lambda r: (str(r.get("as_of_date") or ""), str(r.get("observation_id") or "")))

    events.extend(expansion)
    if overrides_path.is_file():
        events = apply_overrides(events, load_json(overrides_path))

    overlap = sorted(hist_ids & {str(e.get("event_id")) for e in events})
    if overlap:
        raise ValueError(f"off-fixture gold overlaps historical fixture: {overlap[:5]}")

    era_counts: dict[str, int] = {}
    for e in events:
        gid = str(e.get("gold_era_id") or "")
        if gid:
            era_counts[gid] = era_counts.get(gid, 0) + 1

    n_override = sum(1 for e in events if e.get("gold_source") == "human_override")
    return {
        "schema": "logos_chronology_off_fixture_era_gold_v1",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "policy": {"research_only": True, "non_gating": True, "no_trading_signal": True},
        "hypothesis_tier": "[HYPO]",
        "gold_mode": "hardset_v2_plus_blind_split_oov_expansion",
        "cohort_definition": {
            "disjoint_from_historical_gold": True,
            "historical_gold_event_count": len(hist_ids),
            "includes_hardset_news_v2": hardset_gold_path.is_file(),
            "includes_blind_split_oov_expansion": bool(expansion),
            "n_hardset_base": sum(1 for e in events if e.get("cohort") == "off_fixture_hardset_v2"),
            "n_oov_expansion": len(expansion),
        },
        "inputs": {
            "historical_gold_json": str(hist_gold_path.relative_to(ROOT)).replace("\\", "/"),
            "hardset_gold_json": str(hardset_gold_path.relative_to(ROOT)).replace("\\", "/")
            if hardset_gold_path.is_file()
            else None,
            "blind_split_jsonl": str(blind_split_path.relative_to(ROOT)).replace("\\", "/")
            if blind_split_path.is_file()
            else None,
            "expansion_news_jsonl": str(expansion_news_path.relative_to(ROOT)).replace("\\", "/")
            if expansion_news_path.is_file()
            else None,
            "chronology_json": str(chrono_path.name),
            "modern_boost": modern_boost,
            "boost_policy": boost_policy,
            "max_expansion_rows": max_expansion_rows,
            "min_words": min_words,
            "overrides_json": str(overrides_path.name) if overrides_path.is_file() else None,
        },
        "era_id_distribution": era_counts,
        "n_events": len(events),
        "n_human_overrides": n_override,
        "events": events,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical-gold-json", type=Path, default=DEFAULT_HIST_GOLD)
    ap.add_argument("--hardset-gold-json", type=Path, default=DEFAULT_HARDSET_GOLD)
    ap.add_argument("--blind-split-jsonl", type=Path, default=DEFAULT_BLIND_SPLIT)
    ap.add_argument("--expansion-news-jsonl", type=Path, default=DEFAULT_EXPANSION_NEWS)
    ap.add_argument("--hardset-news-jsonl", type=Path, default=DEFAULT_HARDSET_NEWS)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONO)
    ap.add_argument("--overrides-json", type=Path, default=DEFAULT_OVERRIDES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", choices=["global", "tier_v1"], default="tier_v1")
    ap.add_argument("--max-expansion-rows", type=int, default=40)
    ap.add_argument("--min-words", type=int, default=8)
    args = ap.parse_args()

    def _resolve(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    hist = _resolve(args.historical_gold_json)
    hard_gold = _resolve(args.hardset_gold_json)
    blind = _resolve(args.blind_split_jsonl)
    expansion_news = _resolve(args.expansion_news_jsonl)
    hard_news = _resolve(args.hardset_news_jsonl)
    chrono = _resolve(args.chronology_json)
    overrides = _resolve(args.overrides_json)
    out = _resolve(args.output_json)

    if not hist.is_file() or not chrono.is_file():
        print("MISSING historical gold or chronology", file=sys.stderr)
        return 2

    doc = build_off_fixture_gold(
        hist_gold_path=hist,
        hardset_gold_path=hard_gold,
        blind_split_path=blind,
        expansion_news_path=expansion_news,
        hardset_news_path=hard_news,
        chrono_path=chrono,
        overrides_path=overrides,
        modern_boost=float(args.modern_boost),
        boost_policy=str(args.boost_policy),
        max_expansion_rows=int(args.max_expansion_rows),
        min_words=int(args.min_words),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cd = doc["cohort_definition"]
    print(
        json.dumps(
            {
                "ok": True,
                "n_events": doc["n_events"],
                "n_hardset_base": cd["n_hardset_base"],
                "n_oov_expansion": cd["n_oov_expansion"],
                "output_json": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
