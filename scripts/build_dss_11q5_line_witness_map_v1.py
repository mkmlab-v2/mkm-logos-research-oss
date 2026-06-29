#!/usr/bin/env python3
"""11Q5 ETCBC line-level witness map for ENTRY_12/13 (Ps.4.6, Ps.5.2) [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.shadow_lane_gematria_common_v1 import (
    DSS_ORIGINAL,
    gematria_from_text,
    hebrew_tokens,
    load_canon_verse,
    mapping_status_for_score,
)

OUT_DEFAULT = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"

TARGETS = [
    {
        "entry_id": "ENTRY_12",
        "canon_verse_id": "Ps.4.6",
        "scroll": "11Q5",
        "lemma_bonus": {"זבח", "זבחו", "זבחי", "צדק", "צדקה", "בטח", "יהוה", "אל"},
    },
    {
        "entry_id": "ENTRY_13",
        "canon_verse_id": "Ps.5.2",
        "scroll": "11Q5",
        "lemma_bonus": {"יהוה", "אמר", "האזינה", "בינה", "הגיג", "הגיגי", "אזן", "שמע"},
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_scroll_lines(scroll: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not DSS_ORIGINAL.is_file():
        return rows
    with DSS_ORIGINAL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("scroll") or "") != scroll:
                continue
            text = str(row.get("text") or "")
            rows.append({**row, "tokens": hebrew_tokens(text)})
    return rows


def _score_line(canon: dict[str, Any], row: dict[str, Any], lemma_bonus: set[str]) -> tuple[float, int, int]:
    ct = canon["tokens"]
    lt = row["tokens"]
    if not ct or not lt:
        return 0.0, 0, 0
    inter = len(ct & lt)
    union = len(ct | lt)
    jaccard = inter / union if union else 0.0
    lemma_hits = len(lemma_bonus & lt)
    score = min(1.0, jaccard + 0.05 * lemma_hits)
    return round(score, 4), inter, lemma_hits


def build() -> dict[str, Any]:
    scroll_lines = _load_scroll_lines("11Q5")
    entries: list[dict[str, Any]] = []
    for target in TARGETS:
        canon = load_canon_verse(target["canon_verse_id"])
        if not canon:
            continue
        lemma_bonus = set(target["lemma_bonus"])
        scored: list[dict[str, Any]] = []
        for row in scroll_lines:
            score, shared_tokens, lemma_hits = _score_line(canon, row, lemma_bonus)
            if score <= 0 and lemma_hits == 0:
                continue
            text = str(row.get("text") or "")
            g = gematria_from_text(text)
            status = mapping_status_for_score(score, lemma_hits)
            scored.append(
                {
                    "witness_id": str(row.get("id") or ""),
                    "scroll": row.get("scroll"),
                    "line": row.get("line"),
                    "tf_line_node": row.get("tf_line_node"),
                    "text_preview": text[:120],
                    "gematria": g,
                    "mapping_score": score,
                    "shared_token_count": shared_tokens,
                    "lemma_hit_count": lemma_hits,
                    "mapping_status": status,
                    "comparison_type": "lexical_proximity_not_verified_line"
                    if status != "verified_line_witness"
                    else "verified_line_witness",
                }
            )
        scored.sort(key=lambda x: (x["mapping_score"], x["lemma_hit_count"]), reverse=True)
        top = scored[:8]
        entries.append(
            {
                "entry_id": target["entry_id"],
                "canon_verse_id": target["canon_verse_id"],
                "scroll": target["scroll"],
                "canon_gematria": canon["gematria"],
                "canon_text_preview": canon["text"][:120],
                "witness_count": len(top),
                "witnesses": top,
                "anchor_policy": "partial_anchor_verified_scroll_line_buckets",
                "direct_verse_line_mapping": "TBD",
            }
        )

    verified = sum(1 for e in entries for w in e["witnesses"] if w["mapping_status"] == "verified_line_witness")
    provisional = sum(1 for e in entries for w in e["witnesses"] if w["mapping_status"] == "provisional_lexical_anchor")

    return {
        "schema": "dss_11q5_line_witness_map_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "track_a_bridge": False,
        },
        "summary": {
            "targets": len(entries),
            "scroll_line_pool": len(scroll_lines),
            "witness_rows": sum(e["witness_count"] for e in entries),
            "verified_line_witness_rows": verified,
            "provisional_lexical_anchor_rows": provisional,
        },
        "entries": entries,
        "reproduce": "py scripts/build_dss_11q5_line_witness_map_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("targets") or 0) >= 2 and int(sm.get("provisional_lexical_anchor_rows") or 0) >= 4
    print(json.dumps({"ok": ok, "summary": sm, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
