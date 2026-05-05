#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.4, M:0.5}
# Balance: 90
# Purpose: Inject external Bible cross-reference baseline facts into B-track anchor-news tagging artifact.
# Keywords: btrack, json, builder, external baseline, anchor tagging
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"json must be object: {path}")
    return data


def select_fact(registry: dict[str, Any], fact_id: str) -> dict[str, Any]:
    rows = registry.get("facts")
    if not isinstance(rows, list):
        raise SystemExit("invalid fact registry: missing facts list")
    for row in rows:
        if isinstance(row, dict) and row.get("fact_id") == fact_id:
            return row
    raise SystemExit(f"fact_id not found: {fact_id}")


def build_external_fact_view(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": fact.get("fact_id"),
        "classification": fact.get("classification"),
        "label": fact.get("label"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "source_url": fact.get("source_url"),
        "concrete_details": fact.get("concrete_details", {}),
        "scope_note": fact.get("scope_note"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Inject external reference FACT baseline into B-track genesis anchor tagging artifact."
    )
    ap.add_argument(
        "--fact-registry-json",
        default="docs/final/artifacts/btrack_external_reference_fact_registry_v1.json",
    )
    ap.add_argument(
        "--fact-id",
        default="external_bible_crossref_edges_2007_kjv_v1",
    )
    ap.add_argument(
        "--tagging-json",
        default="docs/final/artifacts/btrack_genesis_anchor_news_tagging_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/btrack_genesis_anchor_news_tagging_latest.json",
    )
    args = ap.parse_args()

    fact_registry_path = resolve(args.fact_registry_json)
    tagging_path = resolve(args.tagging_json)
    output_path = resolve(args.output_json)
    if not fact_registry_path.is_file():
        raise SystemExit(f"missing fact registry json: {fact_registry_path}")
    if not tagging_path.is_file():
        raise SystemExit(f"missing tagging json: {tagging_path}")

    fact_registry = load_json(fact_registry_path)
    tagging = load_json(tagging_path)
    selected_fact = select_fact(fact_registry, args.fact_id)
    fact_view = build_external_fact_view(selected_fact)

    tagging["generated_at_utc"] = now_utc()
    tagging["external_reference_fact"] = fact_view

    entries = tagging.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            anchor = entry.get("anchor_evidence")
            if not isinstance(anchor, dict):
                continue
            anchor["external_reference_fact"] = {
                "fact_id": fact_view.get("fact_id"),
                "value": fact_view.get("value"),
                "unit": fact_view.get("unit"),
                "source_url": fact_view.get("source_url"),
                "chapter_count": fact_view.get("concrete_details", {}).get("chapter_count"),
                "cross_reference_count": fact_view.get("concrete_details", {}).get("cross_reference_count"),
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tagging, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
