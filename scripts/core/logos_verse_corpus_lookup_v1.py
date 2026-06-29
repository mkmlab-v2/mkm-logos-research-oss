"""Logos verse corpus lookup (31102 pipeline) — verse_id index + alias normalization."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data" / "logos" / "verse_4pipeline_full_31102.json"

# Registry motif refs → corpus verse_id (Logos canon in verse_4pipeline_full_31102.json)
VERSE_ID_ALIASES: dict[str, str] = {
    "Exo.": "Exod.",
    "Mat.": "Matt.",
    "Mar.": "Mark.",
    "Mk.": "Mark.",
    "Psa.": "Ps.",
    "1Co.": "1Cor.",
    "2Co.": "2Cor.",
    "2Pe.": "2Pet.",
    "1Pe.": "1Pet.",
    "Luk.": "Luke.",
    "Act.": "Acts.",
    "Pro.": "Prov.",
    "Phm.": "Phlm.",
}


def normalize_verse_ref(ref: str) -> str:
    v = ref.strip()
    for src, dst in VERSE_ID_ALIASES.items():
        if v.startswith(src):
            return dst + v[len(src) :]
    return v


def strip_greek_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def extract_greek_text(row: dict[str, Any]) -> str:
    p3 = row.get("pipeline3_gematria_jema12") or {}
    gr = p3.get("gematria_result") or {}
    text = str(gr.get("text") or "").strip()
    if text:
        return text
    return str(row.get("text_preview") or "").strip()


def extract_reconstructed_clause(raw: str, lemma: str) -> str:
    if not raw:
        return lemma
    if not lemma:
        return raw
    raw_n = strip_greek_accents(raw.lower())
    lemma_n = strip_greek_accents(lemma.lower())
    idx = raw_n.find(lemma_n)
    if idx < 0:
        return lemma
    # expand to word boundaries (whitespace/punctuation)
    start = idx
    while start > 0 and raw[start - 1] not in " \t\n,;·":
        start -= 1
    end = idx + len(lemma)
    while end < len(raw) and raw[end] not in " \t\n,;·":
        end += 1
    clause = raw[start:end].strip()
    return clause or lemma


@lru_cache(maxsize=2)
def load_corpus_index(corpus_path: str) -> dict[str, dict[str, Any]]:
    path = Path(corpus_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("corpus must be JSON array")
    return {str(r["verse_id"]): r for r in data if isinstance(r, dict) and r.get("verse_id")}


def lookup_verse(ref: str, *, corpus_path: Path = DEFAULT_CORPUS) -> dict[str, Any] | None:
    index = load_corpus_index(str(corpus_path.resolve()))
    canon = normalize_verse_ref(ref)
    row = index.get(canon)
    if row is None:
        return None
    raw = extract_greek_text(row)
    return {
        "verse_id": canon,
        "registry_ref": ref,
        "raw": raw,
        "text_preview": str(row.get("text_preview") or ""),
        "pipeline2_total": (row.get("pipeline2_gematria_general") or {}).get("total_value"),
        "pipeline3_total": ((row.get("pipeline3_gematria_jema12") or {}).get("gematria_result") or {}).get(
            "total_value"
        ),
    }
