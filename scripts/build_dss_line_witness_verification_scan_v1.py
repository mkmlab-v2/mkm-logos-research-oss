#!/usr/bin/env python3
"""Strict auto-scan for ENTRY_12/13 line↔MT verse verification candidates [HYPO]."""

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
    hebrew_tokens,
    load_canon_verse,
    norm_hebrew,
)

OUT_DEFAULT = ROOT / "reports/dss_line_witness_verification_scan_v1_latest.json"

TARGETS = [
    {"entry_id": "ENTRY_12", "canon_verse_id": "Ps.4.6", "scroll": "11Q5"},
    {"entry_id": "ENTRY_13", "canon_verse_id": "Ps.5.2", "scroll": "11Q5"},
]

VERIFIED_MIN_SUBSTRING = 12
VERIFIED_MIN_JACCARD = 0.85
CANDIDATE_MIN_SUBSTRING = 8
CANDIDATE_MIN_JACCARD = 0.50


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_contiguous_substring(a: str, b: str) -> int:
    if not a or not b:
        return 0
    best = 0
    for n in range(min(len(a), len(b)), 4, -1):
        for i in range(len(a) - n + 1):
            sub = a[i : i + n]
            if sub in b:
                return n
        if best:
            break
    return best


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _scan_entry(target: dict[str, str]) -> dict[str, Any]:
    canon = load_canon_verse(target["canon_verse_id"])
    if not canon:
        return {"entry_id": target["entry_id"], "error": "canon_missing", "candidates": []}
    cnorm = canon["norm"]
    ctoks = canon["tokens"]
    scroll = target["scroll"]
    rows: list[dict[str, Any]] = []
    if DSS_ORIGINAL.is_file():
        with DSS_ORIGINAL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if str(row.get("scroll") or "") != scroll:
                    continue
                text = str(row.get("text") or "")
                nnorm = norm_hebrew(text)
                ltoks = hebrew_tokens(text)
                sub_len = _max_contiguous_substring(cnorm, nnorm)
                jac = round(_jaccard(ctoks, ltoks), 4)
                if sub_len < 5 and jac < 0.08:
                    continue
                if sub_len >= VERIFIED_MIN_SUBSTRING or jac >= VERIFIED_MIN_JACCARD:
                    tier = "verified_line_witness"
                elif sub_len >= CANDIDATE_MIN_SUBSTRING or jac >= CANDIDATE_MIN_JACCARD:
                    tier = "strong_candidate"
                else:
                    tier = "weak_candidate"
                rows.append(
                    {
                        "witness_id": row.get("id"),
                        "line": row.get("line"),
                        "text_preview": text[:100],
                        "contiguous_substring_len": sub_len,
                        "token_jaccard": jac,
                        "verification_tier": tier,
                    }
                )
    rows.sort(key=lambda x: (x["contiguous_substring_len"], x["token_jaccard"]), reverse=True)
    verified = [r for r in rows if r["verification_tier"] == "verified_line_witness"]
    return {
        "entry_id": target["entry_id"],
        "canon_verse_id": target["canon_verse_id"],
        "scroll": scroll,
        "canon_norm_len": len(cnorm),
        "auto_verified_count": len(verified),
        "strong_candidate_count": sum(1 for r in rows if r["verification_tier"] == "strong_candidate"),
        "top_candidates": rows[:12],
        "auto_verified": verified[:6],
    }


def build() -> dict[str, Any]:
    entries = [_scan_entry(t) for t in TARGETS]
    auto_verified_total = sum(int(e.get("auto_verified_count") or 0) for e in entries)
    return {
        "schema": "dss_line_witness_verification_scan_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "thresholds": {
            "verified_min_substring": VERIFIED_MIN_SUBSTRING,
            "verified_min_jaccard": VERIFIED_MIN_JACCARD,
            "candidate_min_substring": CANDIDATE_MIN_SUBSTRING,
            "candidate_min_jaccard": CANDIDATE_MIN_JACCARD,
        },
        "summary": {
            "entries_scanned": len(entries),
            "auto_verified_total": auto_verified_total,
            "promotion_requires_external_or_manual": auto_verified_total == 0,
        },
        "entries": entries,
        "reproduce": "py scripts/build_dss_line_witness_verification_scan_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("entries_scanned") or 0) >= 2
    print(json.dumps({"ok": ok, "auto_verified_total": sm.get("auto_verified_total"), "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
