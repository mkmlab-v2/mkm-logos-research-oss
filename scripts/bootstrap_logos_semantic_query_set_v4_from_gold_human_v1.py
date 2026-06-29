#!/usr/bin/env python3
"""Materialize logos_semantic_query_set_v4_ko_en_v1.json from commander gold_human (B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def materialize(gold: dict[str, object]) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for it in gold.get("items") or []:
        if not isinstance(it, dict):
            continue
        weak = list(it.get("gold_verse_ids_harness_top1") or it.get("gold_verse_ids_human") or [])[:3]
        row: dict[str, object] = {
            "id": it["id"],
            "query_en": it["query_en"],
            "query_ko": it["query_ko"],
            "gold_verse_ids_weak": weak,
        }
        if it.get("gold_note"):
            row["gold_note"] = it["gold_note"]
        items.append(row)
    return {
        "schema": "logos_semantic_query_set_v4_ko_en_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "ts_utc": _utc_now(),
        "note": (
            "Materialized from logos_semantic_query_gold_human_v1 "
            "(harness_top1 weak proxy for v3_bilingual bootstrap)."
        ),
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true", help="Overwrite existing v4.")
    args = ap.parse_args()

    if args.output_json.is_file() and not args.force:
        print(json.dumps({"ok": True, "skipped": "v4_exists", "path": str(args.output_json)}))
        return 0
    if not args.gold_json.is_file():
        print(f"Missing gold: {args.gold_json}", file=__import__("sys").stderr)
        return 2

    gold = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    doc = materialize(gold)
    if len(doc.get("items") or []) != 12:
        print(json.dumps({"ok": False, "items": len(doc.get("items") or [])}), file=__import__("sys").stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "items": 12, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
