# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.72, L:0.55, K:0.82, M:0.48}
# Balance: 87
# Purpose: Load 보명지주 SCM lexicon v1; token hits for must_keep extension on zone_a_scm.
# Keywords: sasang, lexicon, must_keep, zone_a_scm
"""scm_boming_jiju_lexicon_v1 — staged 보명지주 전용 렉시콘 로더.

JSON SSOT: ``docs/final/artifacts/scm_boming_jiju_lexicon_v1.json`` (schema:
``docs/final/schemas/scm_boming_jiju_lexicon_v1.schema.json``).

Matching follows the same tokenization spirit as ``master_codebook_lexicon_v1_bridge.unicode_word_tokens``:
intersection of lexicon normalized forms with text tokens (length >= 2).

Not wired into production compression by default; call sites must opt in explicitly.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEXICON_PATH = _ROOT / "docs" / "final" / "artifacts" / "scm_boming_jiju_lexicon_v1.json"

_UNICODE_WORD = re.compile(r"\w+", re.UNICODE)

SCHEMA_ID = "scm_boming_jiju_lexicon_v1"


def unicode_word_tokens(raw: str) -> set[str]:
    return {t.lower() for t in _UNICODE_WORD.findall(raw) if t and len(t) >= 2}


@lru_cache(maxsize=4)
def _load_entries(path_str: str) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    path = Path(path_str)
    if not path.is_file():
        return (), {"status": "missing", "path": path_str}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA_ID or not doc.get("boundary_ack"):
        return (), {"status": "invalid", "path": path_str, "reason": "schema_or_boundary"}
    entries = doc.get("entries") or []
    if not isinstance(entries, list):
        return (), {"status": "invalid", "path": path_str, "reason": "entries"}
    clean: list[dict[str, Any]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        term = str(e.get("term", "")).strip()
        if not term:
            continue
        nf = str(e.get("normalized_form", term)).strip().lower()
        clean.append({**e, "term": term, "normalized_form": nf})
    return tuple(clean), {
        "status": "ok",
        "path": path_str,
        "version": doc.get("version"),
        "entry_count": len(clean),
    }


def normalized_forms_set(path: Path | None = None) -> frozenset[str]:
    """All normalized forms for set intersection."""
    p = path or DEFAULT_LEXICON_PATH
    entries, _ = _load_entries(str(p.resolve()))
    return frozenset(e["normalized_form"] for e in entries)


def boming_jiju_hits_for_text(
    raw: str,
    path: Path | None = None,
) -> tuple[set[str], dict[str, Any]]:
    """Return (matched normalized forms present in text, meta)."""
    p = path or DEFAULT_LEXICON_PATH
    entries, meta = _load_entries(str(p.resolve()))
    if meta.get("status") != "ok":
        return set(), meta
    forms = frozenset(e["normalized_form"] for e in entries)
    toks = unicode_word_tokens(raw)
    hits = {h for h in (toks & forms)}
    return hits, {
        **meta,
        "hit_count": len(hits),
        "hits_sample": sorted(hits)[:32],
    }


def entries_by_constitution(
    path: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Group entries by ``sasang_constitution`` (empty groups omitted)."""
    p = path or DEFAULT_LEXICON_PATH
    entries, meta = _load_entries(str(p.resolve()))
    if meta.get("status") != "ok":
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        key = str(e.get("sasang_constitution", "")).strip()
        if not key:
            continue
        out.setdefault(key, []).append(e)
    return out
