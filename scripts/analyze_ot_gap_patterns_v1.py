#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_logos_gap_original_text_v1 import (
    NT_BOOKS,
    _build_wlc_index,
    _iter_queue,
    _load_missing_ids,
)
from scripts.probe_ot_gap_wlc_v1 import mt_to_wlc_candidate

NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
WLC = ROOT / "vault/external_lexicon/sources/openscriptures-morphhb/wlc"


def chapter_verse_count(book: str, ch: int) -> int:
    xml = WLC / f"{book}.xml"
    if not xml.is_file():
        return -1
    root = ET.parse(xml).getroot()
    return len(root.findall(f".//o:chapter[@osisID='{book}.{ch}']/o:verse", NS))


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
    by_book = Counter(v.split(".")[0] for v in ot_miss)
    print("by_book", dict(by_book))
    mapped = unmapped = extra_after_end = 0
    for vid in ot_miss:
        if any(c in idx for c in mt_to_wlc_candidate(vid)):
            mapped += 1
            continue
        book, ch_s, v_s = vid.split(".")
        ch, v = int(ch_s), int(v_s)
        wlc_max = chapter_verse_count(book, ch)
        if wlc_max >= 0 and v > wlc_max:
            extra_after_end += 1
            if extra_after_end <= 6:
                print("EXTRA", vid, f"wlc_ch_{ch}_max={wlc_max}")
        else:
            unmapped += 1
            if unmapped <= 10:
                print("UNMAPPED", vid, f"wlc_ch_max={wlc_max}")
    print("mapped", mapped, "extra_after_wlc_end", extra_after_end, "other", unmapped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
