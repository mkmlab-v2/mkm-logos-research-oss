#!/usr/bin/env python3
"""Enrich MT-only gap stubs with residual taxonomy (variant vs versification vs mapping gap)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_logos_gap_original_text_v1 import NT_BOOKS  # noqa: E402
from scripts.logos_stepbible_versification_v1 import (  # noqa: E402
    DEFAULT_TVTMS,
    load_stepbible_eng_to_greek,
    load_stepbible_eng_to_hebrew,
    stepbible_sblgnt_candidates_for_mt_verse,
)

DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_gap_mt_only_residual_classify_v1_latest.json"

# Well-known TR/KJV-style verses absent from NA28/SBLGNT (B-track reference only).
NT_TEXTUAL_VARIANT_IDS = frozenset(
    {
        "Matt.18.11",
        "Matt.23.14",
        "Mark.7.16",
        "Mark.11.26",
        "Mark.15.28",
        "Luke.17.36",
        "Luke.23.17",
        "Jhn.5.4",
        "Acts.8.37",
        "Acts.15.34",
        "Acts.19.41",
        "Acts.28.29",
        "Rom.16.25",
        "Rom.16.26",
        "Rom.16.27",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _residual_taxonomy(row: dict[str, Any], *, heb_map: dict[str, str], grk_map: dict[str, str]) -> str:
    vid = str(row["verse_id"])
    cause = str(row.get("residual_cause") or "")
    book = vid.split(".")[0]
    if book in NT_BOOKS:
        if vid in NT_TEXTUAL_VARIANT_IDS:
            return "textual_variant_omission"
        sb = stepbible_sblgnt_candidates_for_mt_verse(vid, hebrew_map=heb_map, greek_map=grk_map)
        if sb:
            return "versification_mapping_gap_recoverable"
        return "textual_variant_or_unmapped_nt"
    if cause == "mt_verse_beyond_wlc_chapter_end":
        if book in ("1Kgs", "Ezek"):
            return "versification_numbering_shift"
        return "wlc_chapter_boundary"
    if cause == "versification_rule_gap_despite_wlc_hit":
        return "versification_mapping_gap_recoverable"
    if heb_map.get(vid):
        return "versification_mapping_gap_recoverable"
    return "wlc_versification_unmapped"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.policy_jsonl.is_file():
        print(f"missing policy: {args.policy_jsonl}", file=sys.stderr)
        return 2
    heb_map = load_stepbible_eng_to_hebrew()
    grk_map = load_stepbible_eng_to_greek()
    rows_in = [
        json.loads(line)
        for line in args.policy_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    enriched: list[dict[str, Any]] = []
    for row in rows_in:
        tax = _residual_taxonomy(row, heb_map=heb_map, grk_map=grk_map)
        sb_sbl = stepbible_sblgnt_candidates_for_mt_verse(
            row["verse_id"], hebrew_map=heb_map, greek_map=grk_map
        )
        enriched.append(
            {
                **row,
                "residual_taxonomy": tax,
                "stepbible_sblgnt_candidates": sb_sbl,
                "stepbible_hebrew_target": heb_map.get(row["verse_id"]),
                "recoverable_via_ingest_rule": tax
                in (
                    "versification_numbering_shift",
                    "versification_mapping_gap_recoverable",
                ),
            }
        )
    tax_counts = Counter(r["residual_taxonomy"] for r in enriched)
    recoverable = sum(1 for r in enriched if r["recoverable_via_ingest_rule"])
    doc = {
        "schema": "logos_gap_mt_only_residual_classify_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub_count": len(enriched),
        "recoverable_via_ingest_rule_count": recoverable,
        "residual_taxonomy_counts": dict(sorted(tax_counts.items())),
        "stepbible_tvtms_present": DEFAULT_TVTMS.is_file(),
        "verses": enriched,
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "forbidden_claim": "primary_bhs_sblgnt_decode_for_all_31102",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.output} stubs={len(enriched)} recoverable={recoverable} "
        f"taxonomy={dict(tax_counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
