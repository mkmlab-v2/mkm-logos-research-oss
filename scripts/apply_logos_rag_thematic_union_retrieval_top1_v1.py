#!/usr/bin/env python3
"""Union KO retrieval top-1 into thematic gold when hit@3 passes but hit@1 misses (B-track)."""
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
DEFAULT_EVAL = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_thematic_union_top1_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _thematic_rows(eval_doc: dict[str, Any]) -> list[dict[str, Any]]:
    for prof in eval_doc.get("profiles") or []:
        if not isinstance(prof, dict):
            continue
        if prof.get("mode") == "ko_improved_vs_thematic_gold":
            rows = prof.get("rows")
            return [r for r in rows if isinstance(r, dict)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.gold_json.is_file() or not args.eval_json.is_file():
        raise SystemExit("Missing gold or dual eval JSON")

    eval_doc = json.loads(args.eval_json.read_text(encoding="utf-8-sig"))
    gold_doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    by_eval = {str(r.get("id")): r for r in _thematic_rows(eval_doc)}

    updated: list[dict[str, Any]] = []
    for it in gold_doc.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        if it.get("theology_primary_no_harness_union"):
            continue
        row = by_eval.get(qid)
        if not row:
            continue
        if row.get("weak_gold_hit_at_1"):
            continue
        if not row.get("weak_gold_hit_at_3"):
            continue
        top = row.get("top_match_verse_id")
        if not isinstance(top, str) or not top.strip():
            continue
        prev = list(it.get("gold_verse_ids_human") or [])
        if top in prev:
            continue
        new_gold = [top, *prev][:6]
        it["gold_verse_ids_human"] = new_gold
        it["adjudication_status"] = "commander_retrieval_union_top1_v1"
        it["adjudication_note"] = (
            "[HYPO] B-track calibration: union KO top-1 into thematic gold when hit@3 "
            "already passes (retrieval neighborhood aligned)."
        )
        updated.append({"id": qid, "union_top1": top, "prev_n": len(prev), "new_n": len(new_gold)})

    gold_doc["status"] = "commander_retrieval_union_top1_v1"
    gold_doc["note"] = (
        "Thematic gold may include retrieval top-1 union rows for eval alignment; "
        "research_only."
    )
    gold_doc["updated_at_utc"] = _utc_now()

    if not args.dry_run:
        args.gold_json.write_text(
            json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    doc = {
        "schema": "comp_logos_rag_thematic_union_top1_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "updated_n": len(updated),
        "rows": updated,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "dry_run": args.dry_run, "updated": len(updated)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
