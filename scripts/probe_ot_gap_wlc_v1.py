#!/usr/bin/env python3
"""Probe WLC osisID presence for OT gap verse_ids (diagnostic)."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_logos_gap_original_text_v1 import (  # noqa: E402
    NT_BOOKS,
    _build_wlc_index,
    _iter_queue,
    _load_missing_ids,
)

NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
WLC = ROOT / "vault/external_lexicon/sources/openscriptures-morphhb/wlc"


from scripts.logos_mt_wlc_verse_map_v1 import mt_verse_id_to_wlc_osis_candidates as mt_to_wlc_candidate


def main() -> int:
    want = _load_missing_ids(
        ROOT / "reports/constitution/btrack_pilot/logos_verse_canon_coverage_diff_v1_latest.json"
    )
    idx = _build_wlc_index(WLC)
    filled = {
        json.loads(line)["verse_id"]
        for line in (
            ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    ot_miss = [
        v
        for v in _iter_queue(
            ROOT / "reports/constitution/btrack_pilot/logos_verse_gap_ingest_queue_v1_latest.jsonl"
        )
        if v in want and v not in filled and v.split(".")[0] not in NT_BOOKS
    ]
    mapped = 0
    for vid in ot_miss:
        cands = mt_to_wlc_candidate(vid)
        hit = next((c for c in cands if c in idx), None)
        if hit:
            mapped += 1
            if mapped <= 8:
                print("MAP", vid, "->", hit, (idx[hit] or "")[:50])
    print("ot_miss", len(ot_miss), "mapped_via_rules", mapped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
