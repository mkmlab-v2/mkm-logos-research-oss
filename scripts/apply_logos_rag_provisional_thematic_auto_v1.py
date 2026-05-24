#!/usr/bin/env python3
"""Auto-fill provisional thematic gold from v4 weak stubs + preserve harness top-1 (B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_V4 = ART / "logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"
DEFAULT_SAMPLE = ART / "logos_semantic_query_gold_human_sample_v1.json"
SAMPLE_IDS = frozenset({"q01", "q03", "q04", "q08", "q11"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_items(path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return {str(x.get("id")): x for x in doc.get("items") or [] if isinstance(x, dict)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in (args.gold_json, args.v4_json, args.pack_json):
        if not p.is_file():
            raise SystemExit(f"Missing: {p}")

    gold_doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    v4_by_id = _load_items(args.v4_json)
    pack_by_id = _load_items(args.pack_json)
    sample_by_id = _load_items(args.sample_json) if args.sample_json.is_file() else {}

    updated: list[dict[str, Any]] = []
    for it in gold_doc.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        prow = pack_by_id.get(qid) or {}
        cands = prow.get("candidates_top5") or []
        harness_top1 = None
        if cands and isinstance(cands[0], dict):
            harness_top1 = cands[0].get("verse_id")
        if harness_top1:
            it["gold_verse_ids_harness_top1"] = [harness_top1]

        if qid in sample_by_id:
            src = sample_by_id[qid]
            it["gold_verse_ids_human"] = list(src.get("gold_verse_ids_human") or [])
            it["gold_note"] = src.get("gold_note")
            it["adjudication_status"] = "commander_signed_v1"
            it["adjudication_note"] = "Thematic from sample_v1 (auto refresh)."
            updated.append({"id": qid, "source": "sample_v1", "thematic_n": len(it["gold_verse_ids_human"])})
            continue

        v4 = v4_by_id.get(qid) or {}
        weak = [str(x) for x in (v4.get("gold_verse_ids_weak") or []) if isinstance(x, str) and x.strip()]
        if not weak:
            continue
        prev = it.get("gold_verse_ids_human") or []
        it["gold_verse_ids_human"] = weak
        it["adjudication_status"] = "commander_auto_thematic_v4_weak_v1"
        it["adjudication_note"] = (
            "[HYPO] Auto thematic from logos_semantic_query_set_v4 gold_verse_ids_weak; "
            "not harness top-1 claim. Commander may override."
        )
        if prev != weak:
            updated.append({"id": qid, "source": "v4_weak", "thematic_n": len(weak)})

    gold_doc["status"] = "commander_signed_dual_track_v1"
    gold_doc["signoff"] = "commander_approved"
    gold_doc["auto_provisional_policy"] = "v4_weak_primary"
    gold_doc["updated_at_utc"] = _utc_now()
    gold_doc["note"] = (
        "Dual-track: human=thematic (sample 5 + v4_weak auto 7); harness_top1=KO regression only."
    )

    if not args.dry_run:
        args.gold_json.write_text(json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "updated": updated,
                "gold_json": str(args.gold_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
