"""Canonical verse ref normalization for Logos router/seed compare ([HYPO] B-track)."""
from __future__ import annotations

import re

from scripts.build_logos_gold_query_eval_report_v1 import normalize_verse_ref

BOOK_CANON: dict[str, str] = {
    "1chr": "1Chr",
    "1chronicles": "1Chr",
    "2chr": "2Chr",
    "2chronicles": "2Chr",
    "neh": "Neh",
    "nehemiah": "Neh",
    "dan": "Dan",
    "daniel": "Dan",
    "luke": "Luke",
    "mark": "Mark",
    "matt": "Matt",
    "matthew": "Matt",
    "rev": "Rev",
    "revelation": "Rev",
    "ps": "Ps",
    "psalm": "Ps",
    "lamentations": "Lam",
    "lam": "Lam",
    "proverbs": "Prov",
    "jer": "Jer",
    "jeremiah": "Jer",
    "job": "Job",
    "prov": "Prov",
    "eccl": "Eccl",
    "isa": "Isa",
    "ezek": "Ezek",
    "zech": "Zech",
    "hos": "Hos",
    "rom": "Rom",
    "1cor": "1Cor",
    "2cor": "2Cor",
    "john": "Jhn",
    "jhn": "Jhn",
    "1john": "1John",
    "lev": "Lev",
    "leviticus": "Lev",
    "exod": "Exod",
    "exo": "Exod",
    "deut": "Deut",
    "num": "Num",
    "eph": "Eph",
    "col": "Col",
    "mic": "Mic",
}

# Numbered books (1Chr, 2Cor, …) + plain books — SSOT for ingest/audit filters
VERSE_REF_RE = re.compile(r"^(?:[1-3][A-Za-z]+|[A-Za-z][A-Za-z0-9_]*)\.\d+\.\d+$")


def is_canonical_verse_ref(ref: str) -> bool:
    return bool(VERSE_REF_RE.match(str(ref or "").strip()))


def _parse_verse_ref_body(body: str) -> str:
    parts = body.split("_")
    if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit() and parts[-3].isdigit():
        book = "_".join(parts[:-3])
        return f"{book}.{parts[-3]}.{parts[-2]}"
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        book = "_".join(parts[:-2])
        return f"{book}.{parts[-2]}.{parts[-1]}"
    return body.replace("_", ".")


def canonical_verse_ref(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.startswith("vr_"):
        s = _parse_verse_ref_body(s[3:])
    elif s.startswith("verse_ref:"):
        s = _parse_verse_ref_body(s.split(":", 1)[1])
    else:
        s = normalize_verse_ref(s)
    m = re.match(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$", s)
    if not m:
        return s
    book_key = m.group(1).lower()
    book = BOOK_CANON.get(book_key, m.group(1))
    return f"{book}.{m.group(2)}.{m.group(3)}"
