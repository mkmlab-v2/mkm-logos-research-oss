#!/usr/bin/env python3
"""Expanded grep on haan ijeoma PDFs — OCR-tolerant variants."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/ijeoma/secondary/library_capture/2026-06-28"
OUT = ROOT / "reports/constitution/btrack_pilot/haan_ijoeoma_pdf_grep_expanded_v1_latest.json"
GREP = ROOT / "scripts/grep_cheonyucho_pdf_v1.py"

EXPANDED = [
    "闡幽抄",
    "闡幽草",
    "闡幽",
    "關幽",
    "천유초",
    "천유",
    "精文",
    "韓昌淵",
    "崔謙",
    "東武遺稿",
    "東武遺藁",
    "遺稿抄",
    "遺藁抄",
    "011",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    # patch terms via env by writing temp grep with custom terms - reuse grep script per file
    # grep_cheonyucho_pdf_v1 uses fixed DEFAULT_TERMS; inline extract here for speed
    sys.path.insert(0, str(ROOT))
    from grep_cheonyucho_pdf_v1 import extract_pdf_text, grep_terms

    rows = []
    for pdf in sorted(CORPUS.rglob("*.pdf")):
        rel = pdf.relative_to(ROOT).as_posix()
        try:
            text, backend = extract_pdf_text(pdf)
            hits = grep_terms(text, EXPANDED)
        except Exception as exc:  # noqa: BLE001
            rows.append({"pdf": rel, "error": str(exc)[:200]})
            continue
        score = sum(len(v) for v in hits.values())
        rows.append(
            {
                "pdf": rel,
                "backend": backend,
                "text_len": len(text),
                "term_hit_count": score,
                "terms": list(hits.keys()),
                "cheonyucho_signal": any(t in hits for t in ("闡幽抄", "闡幽草", "闡幽", "천유초")),
            }
        )
    ranked = sorted([r for r in rows if r.get("term_hit_count")], key=lambda x: -x["term_hit_count"])
    doc = {
        "schema": "haan_ijoeoma_pdf_grep_expanded_v1",
        "generated_at_utc": _utc(),
        "pdf_count": len(rows),
        "hit_count": len(ranked),
        "top_hits": ranked[:15],
        "all": rows,
        "reproduce": "py scripts/run_haan_ijoeoma_pdf_grep_expanded_v1.py",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hit_count": len(ranked), "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
