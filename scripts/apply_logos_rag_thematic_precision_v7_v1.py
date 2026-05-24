#!/usr/bin/env python3
"""Apply precision thematic gold for 7 provisional rows (pack rank 2-4 + v4 weak union)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_REVIEW = PILOT / "logos_rag_provisional_thematic_review_v1_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_thematic_precision_v7_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _precision_gold(row: dict[str, Any]) -> list[str]:
    harness = row.get("harness_top1")
    weak = list(row.get("current_thematic_gold") or [])
    pack = row.get("pack_candidates_top5") or []
    out: list[str] = []
    seen: set[str] = set()
    for vid in weak:
        if isinstance(vid, str) and vid.strip() and vid != harness and vid not in seen:
            out.append(vid)
            seen.add(vid)
    for c in pack[1:4]:
        if not isinstance(c, dict):
            continue
        vid = c.get("verse_id")
        if not isinstance(vid, str) or not vid.strip() or vid == harness:
            continue
        if vid not in seen:
            out.append(vid)
            seen.add(vid)
    return out[:4]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--review-json", type=Path, default=DEFAULT_REVIEW)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    review = json.loads(args.review_json.read_text(encoding="utf-8-sig"))
    gold_doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    by_id = {str(x.get("id")): x for x in review.get("items") or [] if isinstance(x, dict)}

    updated: list[dict[str, Any]] = []
    for it in gold_doc.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        row = by_id.get(qid)
        if not row:
            continue
        new_gold = _precision_gold(row)
        prev = it.get("gold_verse_ids_human") or []
        it["gold_verse_ids_human"] = new_gold
        it["adjudication_status"] = "commander_thematic_precision_v1"
        it["adjudication_note"] = (
            "Precision: v4_weak union pack ranks 2-4 (excl harness top-1); max 4 verses."
        )
        updated.append(
            {
                "id": qid,
                "prev_n": len(prev),
                "new_n": len(new_gold),
                "harness_top1": row.get("harness_top1"),
                "new_gold": new_gold,
            }
        )

    gold_doc["status"] = "commander_thematic_precision_v1"
    gold_doc["note"] = "7 provisional rows refined; sample 5 unchanged."
    gold_doc["updated_at_utc"] = _utc_now()
    args.gold_json.write_text(json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    doc = {
        "schema": "comp_logos_rag_thematic_precision_v7_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "updated_n": len(updated),
        "rows": updated,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "updated": len(updated), "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
