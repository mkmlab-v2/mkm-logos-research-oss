#!/usr/bin/env python3
"""Build operator gold for hardset news rows (non-synthetic, no label_guided_seed).

Gold rule (documented, not ML): external_* stress templates -> modern_observational_field.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logos_chronology_map_core_v1 import infer_tags_from_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_blind_split_hardset_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v1_latest.json"
EXCLUDED = frozenset({"label_guided_seed", "manual_seed"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    news_path = args.news_jsonl if args.news_jsonl.is_absolute() else ROOT / args.news_jsonl
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not news_path.is_file():
        print(f"MISSING: {news_path}", file=sys.stderr)
        return 2

    events: list[dict[str, Any]] = []
    for row in _load_jsonl(news_path):
        sid = str(row.get("source_id") or "")
        if sid in EXCLUDED:
            continue
        text = str(row.get("canonical_text") or "")
        tags = infer_tags_from_text(text)
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
                "gold_source": "uniform_modern_rule",
                "gold_era_id": "modern_observational_field",
                "acceptable_era_ids": [
                    "modern_observational_field",
                    "judges_risk_cycle",
                    "exile_and_return",
                ],
                "gold_rationale_ko": (
                    "외부 BTC/매크로 스트레스 템플릿(변동성·리스크오프·지정학·유동성) "
                    "→ 현대 관측 필드 shadow. 신학·가격 예언 단정 아님."
                ),
                "is_synthetic_source": False,
            }
        )

    doc = {
        "schema": "logos_chronology_hardset_news_era_gold_v1",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "policy": {
            "research_only": True,
            "non_gating": True,
            "label_guided_seed_excluded": True,
        },
        "hypothesis_tier": "[HYPO]",
        "excluded_source_ids": sorted(EXCLUDED),
        "inputs": {"news_jsonl": str(news_path.relative_to(ROOT)).replace("\\", "/")},
        "operator_gold_rule": (
            "All hardset rows share stress-keyword templates; primary era=modern_observational_field."
        ),
        "n_events": len(events),
        "events": events,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} n={len(events)}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
