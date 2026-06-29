#!/usr/bin/env python3
"""Triage GraphRAG seed gaps — normalize vs true missing path ([HYPO])."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_RETRIEVAL = ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_seed_gap_triage_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--retrieval-json", type=Path, default=DEFAULT_RETRIEVAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    topics_doc = json.loads(args.topics_json.read_text(encoding="utf-8-sig"))
    retrieval = json.loads(args.retrieval_json.read_text(encoding="utf-8-sig")) if args.retrieval_json.is_file() else {}
    by_topic = {t["topic_id"]: t for t in retrieval.get("topics") or []}

    gaps = []
    for topic in topics_doc.get("topics") or []:
        tid = str(topic.get("topic_id") or "")
        seeds = [canonical_verse_ref(str(s)) for s in (topic.get("seed_verse_ids") or []) if s]
        ref = str(topic.get("graphrag_ref") or "")
        router_path = ROOT / ref if ref else None
        router = json.loads(router_path.read_text(encoding="utf-8-sig")) if router_path and router_path.is_file() else {}
        raw_ids = list(router.get("verse_ids") or [])
        ret = by_topic.get(tid) or {}
        overlap = set(ret.get("seed_router_overlap") or [])
        for sid in seeds:
            if sid in overlap:
                continue
            raw_hits = [r for r in raw_ids if sid.lower() in canonical_verse_ref(str(r)).lower() or canonical_verse_ref(str(r)) == sid]
            gaps.append(
                {
                    "topic_id": tid,
                    "seed_verse_id": sid,
                    "graphrag_ref": ref,
                    "gap_class": "normalize_recoverable" if raw_hits else "path_missing",
                    "raw_router_hits": raw_hits[:5],
                    "remediation_hint": (
                        "Re-run audit with canonical_verse_ref (fixed book alias)."
                        if raw_hits
                        else "Add concept_bridge path terminating at seed verse_id."
                    ),
                }
            )

    doc = {
        "schema": "logos_graphrag_seed_gap_triage_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "summary": {
            "gap_count": len(gaps),
            "normalize_recoverable": sum(1 for g in gaps if g["gap_class"] == "normalize_recoverable"),
            "path_missing": sum(1 for g in gaps if g["gap_class"] == "path_missing"),
        },
        "gaps": gaps,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
