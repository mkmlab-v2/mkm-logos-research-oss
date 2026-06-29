#!/usr/bin/env python3
"""Grep PDF(s) for 천유초 / 闡幽 / related hanja terms; write JSON artifact."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TERMS = [
    "闡幽抄",
    "闡幽草",
    "闡幽",
    "천유초",
    "遺稿抄",
    "遺藁抄",
    "格致藁",
    "東武遺稿",
    "四象草本",
]

CONTEXT = 80


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_pdf_text(path: Path) -> tuple[str, str]:
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path)) or "", "pdfminer.six"
    except ImportError:
        pass
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts), "pypdf"
    except ImportError:
        pass
    raise RuntimeError("Install pdfminer.six or pypdf for PDF grep")


def grep_terms(text: str, terms: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    compact = re.sub(r"\s+", " ", text)
    for term in terms:
        snippets: list[str] = []
        for m in re.finditer(re.escape(term), compact):
            start = max(0, m.start() - CONTEXT)
            end = min(len(compact), m.end() + CONTEXT)
            snip = compact[start:end].strip()
            if snip and snip not in snippets:
                snippets.append(snip)
            if len(snippets) >= 5:
                break
        if snippets:
            hits[term] = snippets
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path, help="PDF path")
    ap.add_argument("--out", type=Path, help="Output JSON (default: reports/.../<stem>_grep.json)")
    ap.add_argument("--citation", default="", help="Bibliographic citation string")
    ap.add_argument("--source-url", default="", help="Download or landing URL")
    ap.add_argument("--arti-id", default="", help="KCI arti id if applicable")
    args = ap.parse_args()

    pdf = args.pdf if args.pdf.is_absolute() else ROOT / args.pdf
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    text, backend = extract_pdf_text(pdf)
    term_hits = grep_terms(text, DEFAULT_TERMS)
    out = args.out
    if out is None:
        out = ROOT / "reports/constitution/btrack_pilot" / f"{pdf.stem}_grep_cheonyucho_v1.json"
    elif not out.is_absolute():
        out = ROOT / out

    doc = {
        "schema": "cheonyucho_pdf_grep_v1",
        "generated_at_utc": _utc(),
        "pdf": str(pdf.relative_to(ROOT)).replace("\\", "/"),
        "source_url": args.source_url or None,
        "citation": args.citation or None,
        "arti_id": args.arti_id or None,
        "backend_used": backend,
        "text_len": len(text),
        "term_hits": term_hits,
        "cheonyucho_in_pdf": bool(term_hits.get("闡幽抄") or term_hits.get("천유초") or term_hits.get("闡幽")),
        "verdict": (
            "mentions_cheonyucho_list_only"
            if term_hits.get("闡幽抄") or term_hits.get("천유초")
            else ("mentions_闡幽_grass_only" if term_hits.get("闡幽草") else "no_cheonyucho_signal")
        ),
        "reproduce": f"py scripts/grep_cheonyucho_pdf_v1.py --pdf {pdf.relative_to(ROOT)}",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "verdict": doc["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
