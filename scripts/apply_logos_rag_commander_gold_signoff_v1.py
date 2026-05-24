#!/usr/bin/env python3
"""Commander sign-off: thematic gold vs KO top-1 harness (dual-track, B-track only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution" / "btrack_pilot"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_SAMPLE = ART / "logos_semantic_query_gold_human_sample_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"
DEFAULT_SIGNOFF = ART / "logos_rag_gold_commander_signoff_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_items(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items")
    if not isinstance(items, list):
        raise ValueError(f"items[] required: {path}")
    return [x for x in items if isinstance(x, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--reviewer", type=str, default="commander")
    ap.add_argument(
        "--l2-provisional-thematic",
        choices=("pack_ranks_2_4", "pack_top3_excl_top1"),
        default="pack_ranks_2_4",
        help="Thematic fill for q without sample: ranks 2-4 from adjudication pack.",
    )
    ap.add_argument("--skip-eval", action="store_true")
    ap.add_argument("--record-l2-approval", action="store_true", help="ACK L2 if gate passes after apply.")
    args = ap.parse_args()

    for p in (args.gold_json, args.pack_json):
        if not p.is_file():
            raise SystemExit(f"Missing: {p}")

    gold_doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    sample_by_id: dict[str, dict[str, Any]] = {}
    if args.sample_json.is_file():
        for it in _load_items(args.sample_json):
            sample_by_id[str(it.get("id") or "")] = it

    pack = json.loads(args.pack_json.read_text(encoding="utf-8-sig"))
    pack_by_id = {str(x.get("id")): x for x in pack.get("items") or [] if isinstance(x, dict)}

    rows: list[dict[str, Any]] = []
    thematic_from_sample = 0
    thematic_provisional = 0

    for it in gold_doc.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        prow = pack_by_id.get(qid) or {}
        cands = prow.get("candidates_top5") or []
        harness_top1 = None
        if cands and isinstance(cands[0], dict):
            harness_top1 = cands[0].get("verse_id")

        if qid in sample_by_id:
            src = sample_by_id[qid]
            thematic = list(src.get("gold_verse_ids_human") or [])
            it["gold_note"] = src.get("gold_note")
            it["adjudication_status"] = "commander_signed_v1"
            it["adjudication_note"] = "Thematic gold from logos_semantic_query_gold_human_sample_v1 (commander sign-off)."
            thematic_from_sample += 1
        else:
            pool: list[str] = []
            if args.l2_provisional_thematic == "pack_ranks_2_4":
                for c in cands[1:4]:
                    if isinstance(c, dict) and isinstance(c.get("verse_id"), str):
                        pool.append(c["verse_id"])
            else:
                for c in cands[:3]:
                    if isinstance(c, dict) and isinstance(c.get("verse_id"), str):
                        vid = c["verse_id"]
                        if vid != harness_top1:
                            pool.append(vid)
            thematic = pool
            it["adjudication_status"] = "commander_signed_v1"
            it["adjudication_note"] = (
                f"L2 provisional thematic ({args.l2_provisional_thematic}); harness top-1 tracked separately."
            )
            thematic_provisional += 1

        it["gold_verse_ids_human"] = thematic
        it["gold_verse_ids_harness_top1"] = [harness_top1] if harness_top1 else []
        overlap = set(thematic) & {harness_top1} if harness_top1 else set()
        rows.append(
            {
                "id": qid,
                "thematic_n": len(thematic),
                "harness_top1": harness_top1,
                "thematic_overlaps_harness": bool(overlap),
                "source": "sample_v1" if qid in sample_by_id else args.l2_provisional_thematic,
            }
        )

    gold_doc["status"] = "commander_signed_dual_track_v1"
    gold_doc["signoff"] = "commander_approved"
    gold_doc["updated_at_utc"] = _utc_now()
    gold_doc["note"] = (
        "Dual-track: gold_verse_ids_human=thematic adjudication; "
        "gold_verse_ids_harness_top1=KO regression harness only (not L2 quality claim)."
    )
    args.gold_json.write_text(json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    eval_summary: dict[str, Any] = {}
    if not args.skip_eval:
        py = sys.executable
        proc = subprocess.run(
            [py, str(ROOT / "scripts/run_logos_rag_dual_gold_eval_v1.py")],
            cwd=str(ROOT),
        )
        eval_path = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"
        if eval_path.is_file():
            eval_summary = json.loads(eval_path.read_text(encoding="utf-8")).get("summary") or {}

    signoff_doc = {
        "schema": "logos_rag_gold_commander_signoff_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "reviewer": args.reviewer,
        "decision": "ACK_DUAL_TRACK_GOLD",
        "policy": {
            "thematic_field": "gold_verse_ids_human",
            "harness_field": "gold_verse_ids_harness_top1",
            "thematic_sample_pairs": 5,
            "thematic_provisional_pairs": thematic_provisional,
            "l2_provisional_rule": args.l2_provisional_thematic,
            "forbidden_claim": "Do not cite harness hit@1 as thematic retrieval quality or Track A proof.",
        },
        "items": rows,
        "eval_summary": eval_summary,
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "a_track_auto_promotion": False,
        },
    }
    args.signoff_json.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_json.write_text(json.dumps(signoff_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    l2_recorded = False
    if args.record_l2_approval:
        gate_proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_logos_rag_btrack_promotion_gate_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        gate = json.loads((ART / "logos_rag_btrack_promotion_gate_v1_latest.json").read_text(encoding="utf-8-sig"))
        l2_ready = (gate.get("tiers") or {}).get("L2_track_c_shadow_ingest", {}).get("approval_ready")
        if l2_ready or gate_proc.returncode == 0:
            rec = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/record_logos_rag_btrack_promotion_human_approval_v1.py"),
                    "--tier",
                    "L2",
                    "--notes",
                    "Dual-track gold sign-off: thematic vs harness_top1 separated.",
                ],
                cwd=str(ROOT),
            )
            l2_recorded = rec.returncode == 0

    print(
        json.dumps(
            {
                "ok": True,
                "gold_json": str(args.gold_json),
                "signoff_json": str(args.signoff_json),
                "thematic_from_sample": thematic_from_sample,
                "thematic_provisional": thematic_provisional,
                "eval_summary": eval_summary,
                "l2_approval_recorded": l2_recorded,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
