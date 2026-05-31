#!/usr/bin/env python3
"""Fetch and parse Qumran-Digital 11Q20 transcription for ENTRY_07 comparandum [HYPO]."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://lexicon.qumran-digital.org/transcriptions/11Q20/2025-11-11/index.html"
OUT_JSON = ROOT / "reports" / "qd_11q20_transcription_extract_latest.json"
OUT_HTML = ROOT / "reports" / "qd_11q20_transcription_raw_latest.html"
TARGET_COLS_ROMAN = ("XLVI", "XLVII")
TARGET_COLS_INT = (46, 47)

UA = "MKM-research/1.0 (fetch_qumran_digital_11q20_transcription_v1)"


def fetch_html() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def parse_fragment_columns(body: str) -> list[dict]:
    """QD 11Q20 uses <details><summary>N</summary> fragment columns (not 11Q19 col XLVI)."""
    fragments: list[dict] = []
    for m in re.finditer(
        r"<details><summary>(\d{1,3})</summary>(.*?)</details>",
        body,
        re.S | re.I,
    ):
        frag_no = int(m.group(1))
        block = m.group(2)
        line_refs: list[dict] = []
        for lm in re.finditer(
            r'<a\s+href="#([^"]+)"[^>]*>\s*(\d{1,3})\s*</a>',
            block,
            re.I,
        ):
            line_refs.append(
                {"anchor_id": lm.group(1), "line_number": int(lm.group(2))}
            )
        fragments.append(
            {
                "qd_fragment_column": frag_no,
                "line_ref_count": len(line_refs),
                "line_refs_sample": line_refs[:5],
            }
        )
    return fragments


def extract_line_text(body: str, anchor_id: str, max_chars: int = 4000) -> str:
    marker = f'id="{anchor_id}"'
    start = body.find(marker)
    if start < 0:
        return ""
    chunk = body[start : start + max_chars]
    hebrew = re.findall(r"[\u0590-\u05FF][\u0590-\u05FF\s◦\[\]—\-·.]{2,}", chunk)
    if not hebrew:
        return strip_tags(chunk)[:400]
    return max(hebrew, key=len).strip()[:500]


def extract_fragment_column_lines(body: str, fragment_no: int, max_lines: int = 30) -> list[dict]:
    m = re.search(
        rf"<details><summary>{fragment_no}</summary>(.*?)</details>",
        body,
        re.S | re.I,
    )
    if not m:
        return []
    block = m.group(1)
    rows: list[dict] = []
    for lm in re.finditer(
        r'<a\s+href="#([^"]+)"[^>]*>\s*(\d{1,3})\s*</a>',
        block,
        re.I,
    ):
        aid, line_no = lm.group(1), int(lm.group(2))
        text = extract_line_text(body, aid)
        rows.append(
            {
                "line": line_no,
                "anchor_id": aid,
                "text": text,
                "has_hebrew": bool(re.search(r"[\u0590-\u05FF]", text)),
            }
        )
        if len(rows) >= max_lines:
            break
    return rows


def main() -> int:
    body = fetch_html()
    OUT_HTML.write_text(body, encoding="utf-8")

    fragments = parse_fragment_columns(body)
    frag_nums = [f["qd_fragment_column"] for f in fragments]
    max_frag = max(frag_nums) if frag_nums else 0

    target_extracts: list[dict] = []
    for col_int, col_roman in zip(TARGET_COLS_INT, TARGET_COLS_ROMAN):
        target_extracts.append(
            {
                "column_number_11q19_roman": col_roman,
                "column_number_11q19_int": col_int,
                "entry_07_target": True,
                "status": "not_on_11q20_qd_page",
                "reason": (
                    f"QD 11Q20 page lists fragment columns 1–{max_frag} only; "
                    "no XLVI/XLVII (46/47) anchors."
                ),
                "lines": [],
                "line_count": 0,
            }
        )

    # Demonstrate line-level extraction on fragment col 5 (has lines 9–20 in TOC sample)
    demo_frag = 5 if 5 in frag_nums else (frag_nums[0] if frag_nums else None)
    demo_lines: list[dict] = []
    if demo_frag is not None:
        demo_lines = extract_fragment_column_lines(body, demo_frag, max_lines=25)

    roman_hits = {r: len(re.findall(r, body, re.I)) for r in TARGET_COLS_ROMAN}
    line_ids = len(re.findall(r'id="c\d+-i\d+"', body))

    payload = {
        "schema": "qd_11q20_transcription_extract_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_url": URL,
        "source_manuscript": "11Q20",
        "comparandum_for": "11Q19_ENTRY_07_cols_XLVI_XLVII",
        "track": "B-track",
        "research_only": True,
        "hypo": True,
        "html_bytes": len(body.encode("utf-8")),
        "qd_fragment_columns_count": len(fragments),
        "qd_fragment_column_range": [min(frag_nums), max_frag] if frag_nums else None,
        "line_anchor_ids_count": line_ids,
        "roman_numeral_hits_in_html": roman_hits,
        "target_11q19_column_extracts": target_extracts,
        "demo_fragment_column_lines": {
            "qd_fragment_column": demo_frag,
            "purpose": "prove line-level Hebrew extraction works on QD HTML",
            "line_count": len(demo_lines),
            "lines_with_hebrew": sum(1 for x in demo_lines if x.get("has_hebrew")),
            "lines": demo_lines,
        },
        "entry_07_conclusion": (
            "Cannot auto-fill 11Q19 cols XLVI-XLVII from 11Q20 QD: witness is partial (cols 1-"
            f"{max_frag}) with different column numbering. IAA/DJD/Yadin or future QD 11Q19 "
            "transcription required for ENTRY_07 line anchor."
        ),
        "crosswalk_note": (
            "11Q20 Temple Scroll b is parallel literature, not column-index substitute for 11Q19."
        ),
        "raw_html_path": str(OUT_HTML.relative_to(ROOT)).replace("\\", "/"),
        "ssot_mutation": False,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT_JSON),
                "qd_fragment_range": payload.get("qd_fragment_column_range"),
                "demo": payload.get("demo_fragment_column_lines"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
