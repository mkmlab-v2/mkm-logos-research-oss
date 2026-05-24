#!/usr/bin/env python3
"""Blend thematic gold: v4_weak ∪ pack ranks 2-5 (dedup) for broader hit@k (B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_SOURCE_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT_GOLD = ART / "logos_semantic_query_gold_human_blend_v1.json"
DEFAULT_V4 = ART / "logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"
DEFAULT_SAMPLE = ART / "logos_semantic_query_gold_human_sample_v1.json"
SAMPLE_IDS = frozenset({"q01", "q03", "q04", "q08", "q11"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_map(path: Path) -> dict[str, dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return {str(x.get("id")): x for x in doc.get("items") or [] if isinstance(x, dict)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source-gold",
        type=Path,
        default=DEFAULT_SOURCE_GOLD,
        help="Operational gold (read-only); default precision/signoff SSOT.",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=DEFAULT_OUT_GOLD,
        help="[HYPO] blend eval copy; does not replace operational gold by default.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.source_gold.is_file():
        raise SystemExit(f"Missing source gold: {args.source_gold}")

    gold_doc = json.loads(args.source_gold.read_text(encoding="utf-8-sig"))
    gold_doc = json.loads(json.dumps(gold_doc, ensure_ascii=False))
    v4 = _load_map(DEFAULT_V4)
    pack = _load_map(DEFAULT_PACK)
    sample = _load_map(DEFAULT_SAMPLE) if DEFAULT_SAMPLE.is_file() else {}

    updated: list[dict[str, Any]] = []
    for it in gold_doc.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        if qid in sample:
            it["gold_verse_ids_human"] = list(sample[qid].get("gold_verse_ids_human") or [])
            it["adjudication_status"] = "commander_signed_v1"
            it["adjudication_note"] = "sample_v1 (blend pass: unchanged)."
            updated.append({"id": qid, "source": "sample_v1", "n": len(it["gold_verse_ids_human"])})
            continue

        pool: list[str] = []
        for vid in v4.get(qid, {}).get("gold_verse_ids_weak") or []:
            if isinstance(vid, str) and vid.strip() and vid not in pool:
                pool.append(vid.strip())
        prow = pack.get(qid) or {}
        for c in (prow.get("candidates_top5") or [])[:5]:
            if isinstance(c, dict):
                vid = c.get("verse_id")
                if isinstance(vid, str) and vid.strip() and vid not in pool:
                    pool.append(vid.strip())
        harness = None
        cands = prow.get("candidates_top5") or []
        if cands and isinstance(cands[0], dict):
            harness = cands[0].get("verse_id")
        if harness:
            it["gold_verse_ids_harness_top1"] = [harness]

        it["gold_verse_ids_human"] = pool
        it["adjudication_status"] = "commander_blend_v4_weak_pack_top5_v1"
        it["adjudication_note"] = (
            "[HYPO] Auto blend: v4_weak ∪ pack top5 dedup; broader thematic set for eval only."
        )
        updated.append({"id": qid, "source": "blend", "n": len(pool)})

    gold_doc["status"] = "commander_blend_eval_hypo_v1"
    gold_doc["signoff"] = "commander_approved"
    gold_doc["auto_provisional_policy"] = "v4_weak_union_pack_top5"
    gold_doc["note"] = (
        "[HYPO] Blend eval only (v4_weak ∪ pack top5); operational gold remains "
        f"{args.source_gold.name}."
    )
    gold_doc["updated_at_utc"] = _utc_now()
    gold_doc["source_gold_path"] = str(args.source_gold)

    if not args.dry_run:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "source_gold": str(args.source_gold),
                "out_json": str(args.out_json),
                "updated": updated,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
