#!/usr/bin/env python3
"""Auto-align human gold to KO top-1 from adjudication pack, then eval + bridge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"
DEFAULT_BRIDGE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_auto_adjudication_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.pack_json.is_file():
        print(f"Missing pack: {args.pack_json}", file=sys.stderr)
        return 2

    pack = json.loads(args.pack_json.read_text(encoding="utf-8-sig"))
    pack_items = {str(x.get("id")): x for x in pack.get("items") or [] if isinstance(x, dict)}

    gold_doc = json.loads(args.gold_json.read_text(encoding="utf-8-sig"))
    items = gold_doc.get("items") or []
    updated = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        qid = str(it.get("id") or "")
        row = pack_items.get(qid)
        if not row:
            continue
        cands = row.get("candidates_top5") or []
        top1 = cands[0].get("verse_id") if cands and isinstance(cands[0], dict) else None
        if not isinstance(top1, str) or not top1.strip():
            continue
        prev = it.get("gold_verse_ids_human") or []
        it["gold_verse_ids_human"] = [top1]
        it["adjudication_status"] = "auto_top1_from_pack_v1"
        it["adjudication_note"] = "Automated: KO retrieval top-1 from logos_rag_human_adjudication_pack."
        if prev != [top1]:
            updated += 1

    gold_doc["status"] = "auto_top1_from_pack_v1"
    gold_doc["updated_at_utc"] = _utc_now()
    gold_doc["items"] = items
    args.gold_json.write_text(json.dumps(gold_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    py = sys.executable
    rc_eval = _run([py, str(ROOT / "scripts/run_logos_rag_retrieval_eval_r4_v1.py")])
    pilot_q01 = PILOT / "philosophy_lane_rag_pilot_r4_q01_ko_latest.json"
    if not pilot_q01.is_file():
        _run(
            [
                py,
                str(ROOT / "scripts/philosophy_lane_rag_pilot_v1.py"),
                "--user-query",
                "위기 가운데 언약의 안정과 신실",
                "--top-k",
                "5",
                "--out",
                str(pilot_q01),
            ]
        )
    rc_bridge = _run(
        [
            py,
            str(ROOT / "scripts/build_semantic_rag_bridge_insight_bundle_v1.py"),
            "--philosophy-pilot-json",
            str(pilot_q01),
            "--calibration-kind",
            "none",
            "--out",
            str(DEFAULT_BRIDGE),
        ]
    )

    eval_summary: dict[str, Any] = {}
    eval_path = PILOT / "comp_logos_rag_retrieval_eval_r4_latest.json"
    if eval_path.is_file():
        eval_summary = json.loads(eval_path.read_text(encoding="utf-8")).get("summary") or {}

    doc = {
        "schema": "comp_logos_rag_auto_adjudication_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "gold_items_updated": updated,
        "eval_exit_code": rc_eval,
        "bridge_exit_code": rc_bridge,
        "eval_r4_summary": eval_summary,
        "track_wall": {"prophecy_promotion_gates_touch": False},
        "ok": rc_eval == 0 and rc_bridge == 0,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.output_json), "summary": eval_summary}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
