#!/usr/bin/env python3
"""Export 7 provisional thematic gold rows for commander manual adjudication (B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/logos_rag_gold_commander_signoff_v1_latest.json"
DEFAULT_OUT = PILOT / "logos_rag_provisional_thematic_review_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gold = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    pack = json.loads(args.pack_json.read_text(encoding="utf-8-sig"))
    signoff = json.loads(args.signoff_json.read_text(encoding="utf-8-sig")) if args.signoff_json.is_file() else {}
    pack_by_id = {str(x.get("id")): x for x in pack.get("items") or [] if isinstance(x, dict)}
    sign_by_id = {str(x.get("id")): x for x in signoff.get("items") or [] if isinstance(x, dict)}

    rows: list[dict[str, Any]] = []
    for it in gold.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        sig = sign_by_id.get(qid) or {}
        if sig.get("source") == "sample_v1":
            continue
        note = str(it.get("adjudication_note") or "")
        status = str(it.get("adjudication_status") or "")
        is_provisional = (
            sig.get("source") == "pack_ranks_2_4"
            or "provisional" in note.lower()
            or status.startswith("commander_auto_thematic")
            or status.startswith("commander_thematic_precision")
        )
        if not is_provisional:
            continue
        prow = pack_by_id.get(qid) or {}
        cands = prow.get("candidates_top5") or []
        rows.append(
            {
                "id": qid,
                "query_ko": it.get("query_ko"),
                "query_en": it.get("query_en"),
                "current_thematic_gold": it.get("gold_verse_ids_human") or [],
                "harness_top1": (it.get("gold_verse_ids_harness_top1") or [None])[0],
                "pack_candidates_top5": [
                    {"verse_id": c.get("verse_id"), "score": c.get("score")}
                    for c in cands[:5]
                    if isinstance(c, dict)
                ],
                "suggested_manual_pick": "Replace current_thematic_gold with 1-4 verse_ids from pack (not only rank 2-4).",
            }
        )

    doc = {
        "schema": "logos_rag_provisional_thematic_review_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "provisional_n": len(rows),
        "items": rows,
        "next_command": (
            "Edit logos_semantic_query_gold_human_v1.json gold_verse_ids_human for these ids, "
            "then: py scripts/run_logos_rag_dual_gold_eval_v1.py"
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "provisional_n": len(rows), "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
