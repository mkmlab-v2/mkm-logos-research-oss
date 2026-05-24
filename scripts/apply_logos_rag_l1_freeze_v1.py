#!/usr/bin/env python3
"""Apply L1-approved freeze manifest (pointers only; no Track A / prophecy gates)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution" / "btrack_pilot"
DEFAULT_APPROVAL = ART / "logos_rag_btrack_promotion_human_approval_v1_latest.json"
DEFAULT_OUT = ART / "logos_rag_btrack_l1_bundle_frozen_v1_latest.json"
GOLD = ART / "logos_semantic_query_gold_human_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approval-json", type=Path, default=DEFAULT_APPROVAL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--reset-gold-auto-taint",
        action="store_true",
        help="Clear auto_top1 gold for L2 prep (keeps pack; human gold empty except existing manual).",
    )
    args = ap.parse_args()

    approval_path = args.approval_json if args.approval_json.is_absolute() else ROOT / args.approval_json
    if not approval_path.is_file():
        raise SystemExit(f"Missing approval: {approval_path}")
    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    if str(approval.get("tier")) != "L1":
        raise SystemExit(f"Expected L1 approval, got tier={approval.get('tier')}")

    gold_reset: dict[str, Any] | None = None
    if args.reset_gold_auto_taint and GOLD.is_file():
        gold = json.loads(GOLD.read_text(encoding="utf-8-sig"))
        cleared = 0
        for it in gold.get("items") or []:
            if not isinstance(it, dict):
                continue
            if str(it.get("adjudication_status") or "") == "auto_top1_from_pack_v1":
                it["gold_verse_ids_human"] = []
                it.pop("adjudication_status", None)
                it.pop("adjudication_note", None)
                cleared += 1
        gold["status"] = "partial"
        gold["note"] = "L1 freeze: auto top-1 cleared for L2 human adjudication."
        gold["updated_at_utc"] = _utc_now()
        GOLD.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        gold_reset = {"cleared_auto_items": cleared}

    frozen = {
        "schema": "logos_rag_btrack_l1_bundle_frozen_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "l1_approval": {
            "tier": approval.get("tier"),
            "decision": approval.get("decision"),
            "ts_utc": approval.get("ts_utc"),
            "path": _rel(approval_path),
        },
        "frozen_artifacts": {
            "st_sqlite": _rel(PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"),
            "bridge_bundle": _rel(ART / "semantic_rag_bridge_insight_bundle_v1_latest.json"),
            "merged_pilot": _rel(PILOT / "philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json"),
            "pilot_ssot": _rel(ART / "philosophy_lane_rag_pilot_v1_latest.json"),
            "gate": _rel(ART / "logos_rag_btrack_promotion_gate_v1_latest.json"),
            "eval_r3": _rel(PILOT / "comp_logos_rag_retrieval_eval_r3_latest.json"),
            "eval_r4": _rel(PILOT / "comp_logos_rag_retrieval_eval_r4_latest.json"),
            "adjudication_pack": _rel(PILOT / "logos_rag_human_adjudication_pack_latest.json"),
            "query_set_v4": _rel(ART / "logos_semantic_query_set_v4_ko_en_v1.json"),
        },
        "gold_reset": gold_reset,
        "next_tier": {
            "L2": "Human-sign gold from adjudication pack; target weak_gold hit@3 >= 0.20",
            "blocked_until": ["human_signed_gold", "weak_gold_hit_at_3", "gold_not_auto_tainted"],
        },
        "track_wall": approval.get("track_wall"),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "gold_reset": gold_reset}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
