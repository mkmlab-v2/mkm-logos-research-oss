#!/usr/bin/env python3
"""Build hardset gold v2: rank_top1 heuristic (diversified) + human override merge."""

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
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
DEFAULT_CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_OVERRIDES = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"
EXCLUDED = frozenset({"label_guided_seed", "manual_seed"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONO)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--overrides-json", type=Path, default=DEFAULT_OVERRIDES)
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", choices=["global", "tier_v1"], default="tier_v1")
    args = ap.parse_args()

    news_path = args.news_jsonl if args.news_jsonl.is_absolute() else ROOT / args.news_jsonl
    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    ov_path = args.overrides_json if args.overrides_json.is_absolute() else ROOT / args.overrides_json

    if not news_path.is_file() or not chrono_path.is_file():
        print("MISSING inputs", file=sys.stderr)
        return 2

    chrono = load_json(chrono_path)
    events: list[dict[str, Any]] = []
    era_counts: dict[str, int] = {}

    for row in _load_jsonl(news_path):
        sid = str(row.get("source_id") or "")
        if sid in EXCLUDED:
            continue
        text = str(row.get("canonical_text") or "")
        gold, tags, top3 = rank_top1_era_id(
            chrono,
            text,
            modern_boost=float(args.modern_boost),
            boost_policy=str(args.boost_policy),
        )
        era_counts[gold] = era_counts.get(gold, 0) + 1
        events.append(
            {
                "event_id": f"hardset-{row.get('observation_id')}",
                "tier": "news_hardset",
                "as_of_date": str(row.get("as_of_utc") or "")[:10],
                "partition": row.get("dataset_partition") or "train_holdout",
                "observation_id": row.get("observation_id"),
                "source_id": sid,
                "canonical_text": text,
                "headline_ko": text[:160],
                "inferred_regime_tags_operator": tags,
                "gold_era_id": gold,
                "acceptable_era_ids": [gold, "modern_observational_field", "judges_risk_cycle"],
                "gold_source": "heuristic_rank_top1",
                "gold_rationale_ko": (
                    "text_blind tags + chronology rank top1 (tier_v1 news_hardset). "
                    "Not human-labeled; for text_blind stress test only."
                ),
                "heuristic_top3_era_ids": [r["era_id"] for r in top3],
                "is_synthetic_source": False,
            }
        )

    n_override = 0
    if ov_path.is_file():
        events = apply_overrides(events, load_json(ov_path))
        n_override = sum(1 for e in events if e.get("gold_source") == "human_override")

    era_counts = {}
    for e in events:
        gid = str(e.get("gold_era_id") or "")
        if gid:
            era_counts[gid] = era_counts.get(gid, 0) + 1

    doc = {
        "schema": "logos_chronology_hardset_news_era_gold_v2",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "policy": {"research_only": True, "non_gating": True},
        "hypothesis_tier": "[HYPO]",
        "gold_mode": "rank_top1_with_optional_overrides",
        "inputs": {
            "news_jsonl": str(news_path.name),
            "chronology_json": str(chrono_path.name),
            "modern_boost": float(args.modern_boost),
            "boost_policy": str(args.boost_policy),
            "overrides_json": str(ov_path.name) if ov_path.is_file() else None,
        },
        "era_id_distribution": era_counts,
        "n_events": len(events),
        "n_human_overrides": n_override,
        "events": events,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} n={len(events)} overrides={n_override} eras={era_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
