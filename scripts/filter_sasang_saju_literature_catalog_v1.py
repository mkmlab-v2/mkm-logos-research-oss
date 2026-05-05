#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score-filter JSONL rows from fetch_europepmc_sasang_saju_literature_catalog_v1.py.

Adds ``relevance_score`` and ``relevance_tier`` (high|medium|low) for triage; does not call Europe PMC.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Lowercase matching on title + abstract
_POS = (
    "sasang",
    "constitutional type",
    "constitutional analysis tool",
    "qscc",
    "qscci",
    "spq",
    "sasang personality",
    "tae-yang",
    "tae-eum",
    "so-yang",
    "so-eum",
    "taeyang",
    "taeeum",
    "soyang",
    "soeum",
    "korean medicine",
    "traditional korean medicine",
    "scm",
)
_NEG = (
    "squid game",
    "netflix",
    "fictional character",
    "media character",
    "characters from",
    "protocol for a multicenter",
    "c-scat",
    "sport-related concussion",
    "sport concussion",
    "concussion assessment tool",
)


def _blob(row: dict[str, Any]) -> str:
    t = str(row.get("title") or "")
    a = str(row.get("abstractText") or "")
    return (t + " " + a).lower()


def score_row(row: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    b = _blob(row)
    hits_p = [k for k in _POS if k in b]
    hits_n = [k for k in _NEG if k in b]
    score = float(len(hits_p)) - 0.75 * float(len(hits_n))
    return score, hits_p, hits_n


def tier_for(score: float) -> str:
    if score >= 4.0:
        return "high"
    if score >= 2.0:
        return "medium"
    return "low"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--min-tier",
        choices=("high", "medium", "low"),
        default="medium",
        help="Keep rows at or above this tier (medium includes high)",
    )
    ap.add_argument("--summary", type=Path, default=None, help="Optional JSON summary path")
    args = ap.parse_args()

    tier_order = {"high": 3, "medium": 2, "low": 1}
    floor = tier_order[args.min_tier]

    rows_in = 0
    rows_out = 0
    out_lines: list[dict[str, Any]] = []

    text = args.inp.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows_in += 1
        row = json.loads(line)
        if str(row.get("schema") or "") != "sasang_saju_literature_catalog_row_v1":
            continue
        sc, pos_h, neg_h = score_row(row)
        tr = tier_for(sc)
        if tier_order[tr] < floor:
            continue
        row2 = dict(row)
        row2["relevance_score"] = round(sc, 3)
        row2["relevance_tier"] = tr
        row2["relevance_pos_hits"] = pos_h
        row2["relevance_neg_hits"] = neg_h
        out_lines.append(row2)
        rows_out += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in out_lines:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "schema": "sasang_saju_literature_catalog_filter_summary_v1",
        "in_path": str(args.inp.resolve()),
        "out_path": str(args.out.resolve()),
        "min_tier": args.min_tier,
        "rows_in": rows_in,
        "rows_out": rows_out,
    }
    if args.summary:
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
