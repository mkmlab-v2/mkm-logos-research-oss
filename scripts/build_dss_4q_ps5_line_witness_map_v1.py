#!/usr/bin/env python3
"""4Q83/4Q98b line witness map for ENTRY_13 Ps.5.2 (shadow rail) [HYPO]."""

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
    norm_hebrew,
)

OUT_DEFAULT = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
SCROLLS = ("4Q83", "4Q98b", "4Q98")
LEMMA_BONUS = {"יהוה", "אמר", "האזינה", "בינה", "הגיג", "הגיגי", "אזן", "שמע", "נחני", "דרך"}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_scroll_lines(scrolls: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not DSS_ORIGINAL.is_file():
        return rows
    with DSS_ORIGINAL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            scroll = str(row.get("scroll") or "")
            if scroll not in scrolls:
                continue
            text = str(row.get("text") or "")
            rows.append({**row, "tokens": hebrew_tokens(text), "norm": norm_hebrew(text)})
    return rows


def _score_line(canon: dict[str, Any], row: dict[str, Any]) -> tuple[float, int, int, int]:
    ct = canon["tokens"]
    lt = row["tokens"]
    cnorm = canon["norm"]
    lnorm = row["norm"]
    if not ct or not lt:
        return 0.0, 0, 0, 0
    inter = len(ct & lt)
    union = len(ct | lt)
    jaccard = inter / union if union else 0.0
    lemma_hits = len(LEMMA_BONUS & lt)
    sub_len = 0
    for n in range(min(len(cnorm), len(lnorm)), 5, -1):
        for i in range(len(cnorm) - n + 1):
            if cnorm[i : i + n] in lnorm:
                sub_len = n
                break
        if sub_len:
            break
    score = min(1.0, jaccard + 0.05 * lemma_hits + 0.02 * sub_len)
    return round(score, 4), inter, lemma_hits, sub_len


def build() -> dict[str, Any]:
    canon = load_canon_verse("Ps.5.2")
    if not canon:
        return {"schema": "dss_4q_ps5_line_witness_map_v1", "error": "canon_missing", "entries": []}
    lines = _load_scroll_lines(SCROLLS)
    scored: list[dict[str, Any]] = []
    for row in lines:
        score, shared, lemma_hits, sub_len = _score_line(canon, row)
        if score <= 0 and lemma_hits == 0 and sub_len < 6:
            continue
        text = str(row.get("text") or "")
        g = gematria_from_text(text)
        status = mapping_status_for_score(score, lemma_hits)
        if sub_len >= 12:
            status = "verified_line_witness"
        scored.append(
            {
                "witness_id": row.get("id"),
                "scroll": row.get("scroll"),
                "line": row.get("line"),
                "text_preview": text[:120],
                "gematria": g,
                "mapping_score": score,
                "contiguous_substring_len": sub_len,
                "shared_token_count": shared,
                "lemma_hit_count": lemma_hits,
                "mapping_status": status,
                "comparison_type": "lexical_proximity_not_verified_line"
                if status != "verified_line_witness"
                else "verified_line_witness",
            }
        )
    scored.sort(key=lambda x: (x["mapping_score"], x["contiguous_substring_len"]), reverse=True)
    top = scored[:12]
    provisional = sum(1 for w in top if w["mapping_status"] == "provisional_lexical_anchor")
    hebrew_ok = sum(1 for w in top if int((w.get("gematria") or {}).get("hebrew_chars") or 0) >= 6)
    return {
        "schema": "dss_4q_ps5_line_witness_map_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "entry_id": "ENTRY_13",
        "canon_verse_id": "Ps.5.2",
        "scrolls": list(SCROLLS),
        "canon_gematria": canon["gematria"],
        "summary": {
            "scroll_line_pool": len(lines),
            "witness_rows": len(top),
            "provisional_lexical_anchor_rows": provisional,
            "hebrew_chars_ge_6": hebrew_ok,
        },
        "witnesses": top,
        "reproduce": "py scripts/build_dss_4q_ps5_line_witness_map_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc.get("summary") or {}
    ok = int(sm.get("witness_rows") or 0) >= 4 and int(sm.get("hebrew_chars_ge_6") or 0) >= 4
    print(json.dumps({"ok": ok, "summary": sm, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
