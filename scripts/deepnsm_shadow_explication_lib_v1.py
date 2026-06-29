#!/usr/bin/env python3
"""DeepNSM shadow explication helpers — resolve latin probes to script lexicon forms [HYPO]."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GEMATRIA_LEXICON = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"

_LATIN_DIACRITIC = str.maketrans(
    {
        "ā": "a",
        "ă": "a",
        "ą": "a",
        "ē": "e",
        "ĕ": "e",
        "ę": "e",
        "ī": "i",
        "ĭ": "i",
        "ō": "o",
        "ŏ": "o",
        "ū": "u",
        "ŭ": "u",
        "ḗ": "e",
        "ḝ": "e",
        "ḗ": "e",
        "ḡ": "g",
        "ḫ": "h",
        "ḳ": "k",
        "ḵ": "h",
        "ḏ": "d",
        "ṯ": "t",
        "ṣ": "s",
        "ṭ": "t",
        "ḥ": "h",
        "š": "sh",
        "ś": "s",
    }
)
_STRONGS_RE = re.compile(r"^[GH]\d+$", re.IGNORECASE)


def normalize_latin_translit(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if not s:
        return ""
    s = s.translate(_LATIN_DIACRITIC)
    s = re.sub(r"[.\s\-_'`]+", "", s)
    return s


def normalize_script_form(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def _normalize_strongs(raw: str) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return ""
    if s.isdigit():
        return f"H{s}"
    return s


def _gloss_tokens(gloss: str) -> set[str]:
    out: set[str] = set()
    for part in re.split(r"[,;:()]+", gloss.lower()):
        for word in re.split(r"\s+", part.strip()):
            if len(word) >= 2:
                out.add(word)
    return out


@lru_cache(maxsize=4)
def load_gematria_rows(path_str: str) -> tuple[dict[str, Any], ...]:
    path = Path(path_str)
    if not path.is_file():
        return tuple()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("kernel_recipe_id") or "") != "gematria_bridge_v1":
            continue
        rows.append(row)
    return tuple(rows)


def build_translit_index(rows: tuple[dict[str, Any], ...]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        lang = str(row.get("language") or "").strip().lower()
        if lang not in {"greek", "hebrew", "aramaic"}:
            continue
        norm = normalize_latin_translit(str(row.get("transliteration") or ""))
        if not norm:
            continue
        index.setdefault((lang, norm), []).append(row)
    return index


def _score_row(row: dict[str, Any], probe: str, *, en_hint: str = "") -> int:
    norm = normalize_latin_translit(str(row.get("transliteration") or ""))
    score = 0
    if norm == probe:
        score += 100
    elif norm.startswith(probe) and len(probe) >= 3:
        score += 40
    elif probe in norm and len(probe) >= 4:
        score += 20
    gloss_words = _gloss_tokens(str(row.get("gloss") or ""))
    en_words = _gloss_tokens(en_hint)
    overlap = len(gloss_words & en_words)
    score += overlap * 15
    strongs = _normalize_strongs(str(row.get("strongs") or ""))
    if strongs:
        score += 1
    return score


def resolve_probe_via_gematria(
    probe: str,
    lang: str,
    index: dict[tuple[str, str], list[dict[str, Any]]],
    rows: tuple[dict[str, Any], ...],
    *,
    en_hint: str = "",
) -> dict[str, Any]:
    token = str(probe or "").strip()
    lang_key = str(lang or "").strip().lower()
    norm_probe = normalize_latin_translit(token)
    out: dict[str, Any] = {
        "input": token,
        "language": lang_key,
        "transliteration_norm": norm_probe,
        "lemma_script": "",
        "lemma_norm": "",
        "strongs": "",
        "resolution": "unresolved",
        "candidates_considered": 0,
    }
    if not token or not lang_key:
        out["resolution"] = "empty_probe"
        return out

    candidates: list[dict[str, Any]] = []
    if norm_probe:
        candidates.extend(index.get((lang_key, norm_probe), []))
    if not candidates and len(norm_probe) >= 3:
        for (c_lang, c_norm), bucket in index.items():
            if c_lang != lang_key:
                continue
            if c_norm == norm_probe or (len(norm_probe) >= 4 and c_norm.startswith(norm_probe)):
                candidates.extend(bucket)

    if not candidates and en_hint:
        en_words = _gloss_tokens(en_hint)
        for row in rows:
            if str(row.get("language") or "").lower() != lang_key:
                continue
            if _gloss_tokens(str(row.get("gloss") or "")) & en_words:
                candidates.append(row)

    if not candidates:
        out["resolution"] = "no_gematria_match"
        return out

    out["candidates_considered"] = len(candidates)
    best = max(candidates, key=lambda r: _score_row(r, norm_probe, en_hint=en_hint))
    lemma = str(best.get("lemma") or "")
    out.update(
        {
            "lemma_script": lemma,
            "lemma_norm": normalize_script_form(lemma),
            "strongs": _normalize_strongs(str(best.get("strongs") or "")),
            "transliteration_matched": str(best.get("transliteration") or ""),
            "gloss_matched": str(best.get("gloss") or "")[:120],
            "resolution": "gematria_translit_exact"
            if normalize_latin_translit(str(best.get("transliteration") or "")) == norm_probe
            else "gematria_translit_fuzzy",
        }
    )
    return out


def lookup_tokens_for_resolution(resolved: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for key in ("lemma_norm", "lemma_script", "input", "transliteration_norm"):
        val = str(resolved.get(key) or "").strip()
        if val and val not in tokens:
            tokens.append(val)
    strongs = str(resolved.get("strongs") or "").strip()
    if strongs and _STRONGS_RE.match(strongs) and strongs.lower() not in tokens:
        tokens.append(strongs.lower())
    return tokens


def build_explication_record(
    sample: dict[str, Any],
    *,
    pair_index: int,
    index: dict[tuple[str, str], list[dict[str, Any]]],
    rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    prime_en = str(sample.get("prime_en") or "")
    en_hint = str(lang.get("en") or prime_en or "")
    greek = resolve_probe_via_gematria(
        str(lang.get("greek") or ""),
        "greek",
        index,
        rows,
        en_hint=en_hint,
    )
    hebrew = resolve_probe_via_gematria(
        str(lang.get("hebrew") or ""),
        "hebrew",
        index,
        rows,
        en_hint=en_hint,
    )
    explication = (
        f"[HYPO] NSM prime '{prime_en}' — greek probe resolves to "
        f"{greek.get('lemma_script') or greek.get('resolution')} "
        f"(strongs={greek.get('strongs') or 'n/a'}); hebrew probe resolves to "
        f"{hebrew.get('lemma_script') or hebrew.get('resolution')} "
        f"(strongs={hebrew.get('strongs') or 'n/a'})."
    )
    return {
        "schema": "deepnsm_shadow_explication_v1",
        "pair_index": pair_index,
        "pair_id": f"{prime_en}::{sample.get('variant') or pair_index}",
        "prime_en": prime_en,
        "variant": sample.get("variant"),
        "control": sample.get("control"),
        "lang_probes": lang,
        "resolved_probes": {"greek": greek, "hebrew": hebrew},
        "explication_template": explication,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
    }


def load_explication_sidecar(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    out: dict[str, dict[str, Any]] = {}
    if path.suffix == ".json":
        doc = json.loads(text)
        records = doc.get("records") if isinstance(doc, dict) else doc
        if not isinstance(records, list):
            return {}
        for rec in records:
            if isinstance(rec, dict):
                out[_sidecar_key(rec)] = rec
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if isinstance(rec, dict):
            out[_sidecar_key(rec)] = rec
    return out


def _sidecar_key(rec: dict[str, Any]) -> str:
    prime = str(rec.get("prime_en") or "")
    variant = str(rec.get("variant") or rec.get("pair_index") or "")
    control = str(rec.get("control") or "")
    return f"{prime}|{variant}|{control}"


def sidecar_key_for_sample(sample: dict[str, Any], pair_index: int) -> str:
    return _sidecar_key(
        {
            "prime_en": sample.get("prime_en"),
            "variant": sample.get("variant") or pair_index,
            "control": sample.get("control"),
        }
    )


def clear_gematria_cache() -> None:
    load_gematria_rows.cache_clear()
