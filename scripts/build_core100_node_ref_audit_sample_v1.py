#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Build sampled audit report for verified core100 node->verse mappings.
# Keywords: audit, core100, verified_manual, sample
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def percentile(sorted_vals: list[int], ratio: float) -> int:
    if not sorted_vals:
        return 0
    idx = int(max(0, min(len(sorted_vals) - 1, round((len(sorted_vals) - 1) * ratio))))
    return int(sorted_vals[idx])


def main() -> int:
    ap = argparse.ArgumentParser(description="Build sampled audit report for verified core100 mappings.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--openbible-txt", default="docs/final/artifacts/external_cross_references_openbible/cross_references.txt")
    ap.add_argument("--sample-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-json", default="docs/final/artifacts/core100_node_ref_audit_sample_latest.json")
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    txt_path = resolve(args.openbible_txt)
    out_path = resolve(args.output_json)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")
    if not txt_path.is_file():
        raise SystemExit(f"missing openbible txt: {txt_path}")

    map_doc = json.loads(map_path.read_text(encoding="utf-8"))
    rows = map_doc.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")

    verified = [r for r in rows if isinstance(r, dict) and str(r.get("status", "")) == "verified_manual" and str(r.get("verse_ref", "")).strip()]
    rng = random.Random(int(args.seed))
    sample_size = min(max(1, int(args.sample_size)), len(verified))
    sampled = rng.sample(verified, sample_size) if verified else []

    source_counts: dict[str, int] = {}
    target_counts: dict[str, int] = {}
    vote_sum_by_ref: dict[str, int] = {}
    with txt_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            src = str(row.get("From Verse", "")).strip().replace(":", ".")
            dst = str(row.get("To Verse", "")).strip().replace(":", ".")
            try:
                votes = int(str(row.get("Votes", "0")).strip() or "0")
            except ValueError:
                votes = 0
            if src:
                source_counts[src] = source_counts.get(src, 0) + 1
                vote_sum_by_ref[src] = vote_sum_by_ref.get(src, 0) + max(0, votes)
            if dst:
                target_counts[dst] = target_counts.get(dst, 0) + 1
                vote_sum_by_ref[dst] = vote_sum_by_ref.get(dst, 0) + max(0, votes)

    sampled_vote_sums = [int(vote_sum_by_ref.get(str(r.get("verse_ref", "")).strip(), 0)) for r in sampled]
    sorted_vote_sums = sorted(sampled_vote_sums)
    p50 = percentile(sorted_vote_sums, 0.50)
    p80 = percentile(sorted_vote_sums, 0.80)

    audit_rows: list[dict[str, Any]] = []
    for row in sampled:
        verse_ref = str(row.get("verse_ref", "")).strip()
        votes_sum = int(vote_sum_by_ref.get(verse_ref, 0))
        if votes_sum >= p80:
            votes_band = "high"
        elif votes_sum >= p50:
            votes_band = "medium"
        else:
            votes_band = "low"
        audit_rows.append(
            {
                "node_id": row.get("node_id"),
                "verse_ref": verse_ref,
                "status": row.get("status"),
                "reviewed_by": row.get("reviewed_by", ""),
                "source_match_count": int(source_counts.get(verse_ref, 0)),
                "target_match_count": int(target_counts.get(verse_ref, 0)),
                "vote_sum": votes_sum,
                "vote_confidence_band": votes_band,
                "openbible_presence": bool(source_counts.get(verse_ref, 0) or target_counts.get(verse_ref, 0)),
            }
        )

    out = {
        "schema": "core100_node_ref_audit_sample_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "counts": {
            "verified_total": len(verified),
            "sample_size": sample_size,
            "sample_openbible_presence_count": sum(1 for r in audit_rows if r["openbible_presence"]),
            "sample_vote_band_counts": {
                "high": sum(1 for r in audit_rows if r.get("vote_confidence_band") == "high"),
                "medium": sum(1 for r in audit_rows if r.get("vote_confidence_band") == "medium"),
                "low": sum(1 for r in audit_rows if r.get("vote_confidence_band") == "low"),
            },
            "vote_band_thresholds": {
                "p50_vote_sum": p50,
                "p80_vote_sum": p80,
            },
        },
        "rows": audit_rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
