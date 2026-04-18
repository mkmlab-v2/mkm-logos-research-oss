# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.8, K:0.42, M:0.64}
# Balance: 86
# Purpose: Prefill empty review_status in golden TSV (utt_* -> OK, else PENDING) for workflow bootstrap.
# Keywords: LG, washer, TSV, review, prefill
from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path("C:/workspace")
DEFAULT_TSV = ROOT / "docs" / "final" / "artifacts" / "lg_washer_voice_golden_review_sheet_v1.tsv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    args = ap.parse_args()

    with args.tsv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows:
        raise SystemExit("Empty TSV")
    fieldnames = list(rows[0].keys())

    for r in rows:
        rid = (r.get("id") or "").strip()
        if (r.get("review_status") or "").strip():
            continue
        if rid.startswith("utt_"):
            r["review_status"] = "OK"
            r["reviewer_note"] = (r.get("reviewer_note") or "").strip() or "seed_row_prefill_v1"
        else:
            r["review_status"] = "PENDING"
            r["reviewer_note"] = (r.get("reviewer_note") or "").strip() or "synthetic_review_required"

    with args.tsv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(str(args.tsv))
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
