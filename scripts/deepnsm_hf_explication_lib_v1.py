#!/usr/bin/env python3
"""DeepNSM HF offline stub — gloss-only explication (no translit index) [HYPO]."""
from __future__ import annotations

from typing import Any

from scripts.deepnsm_shadow_explication_lib_v1 import (
    _gloss_tokens,
    _normalize_strongs,
    load_gematria_rows,
    normalize_script_form,
)


def resolve_probe_via_hf_gloss_stub(
    probe: str,
    lang: str,
    rows: tuple[dict[str, Any], ...],
    *,
    en_hint: str = "",
    prime_en: str = "",
) -> dict[str, Any]:
    """Simulate HF semantic explication via gloss overlap only (offline research stub)."""
    token = str(probe or "").strip()
    lang_key = str(lang or "").strip().lower()
    hint_words = _gloss_tokens(en_hint) | _gloss_tokens(prime_en) | _gloss_tokens(token)
    out: dict[str, Any] = {
        "input": token,
        "language": lang_key,
        "transliteration_norm": "",
        "lemma_script": "",
        "lemma_norm": "",
        "strongs": "",
        "resolution": "unresolved",
        "candidates_considered": 0,
        "resolution_backend": "hf_gloss_stub_v1",
    }
    if not token or not lang_key:
        out["resolution"] = "empty_probe"
        return out

    candidates = [r for r in rows if str(r.get("language") or "").lower() == lang_key]
    if not candidates:
        out["resolution"] = "no_lang_rows"
        return out

    def _score(row: dict[str, Any]) -> int:
        gloss_words = _gloss_tokens(str(row.get("gloss") or ""))
        overlap = len(gloss_words & hint_words)
        translit = str(row.get("transliteration") or "").lower()
        score = overlap * 20
        if token.lower() in translit:
            score += 5
        if _normalize_strongs(str(row.get("strongs") or "")):
            score += 1
        return score

    out["candidates_considered"] = len(candidates)
    best = max(candidates, key=_score)
    best_score = _score(best)
    if best_score <= 0:
        out["resolution"] = "no_gloss_overlap"
        return out

    lemma = str(best.get("lemma") or "")
    out.update(
        {
            "lemma_script": lemma,
            "lemma_norm": normalize_script_form(lemma),
            "strongs": _normalize_strongs(str(best.get("strongs") or "")),
            "transliteration_matched": str(best.get("transliteration") or ""),
            "gloss_matched": str(best.get("gloss") or "")[:120],
            "gloss_overlap_score": best_score,
            "resolution": "hf_gloss_stub_match",
        }
    )
    return out


def build_hf_stub_explication_record(
    sample: dict[str, Any],
    *,
    pair_index: int,
    rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    lang = sample.get("lang_probes") if isinstance(sample.get("lang_probes"), dict) else {}
    prime_en = str(sample.get("prime_en") or "")
    en_hint = str(lang.get("en") or prime_en or "")
    greek = resolve_probe_via_hf_gloss_stub(
        str(lang.get("greek") or ""),
        "greek",
        rows,
        en_hint=en_hint,
        prime_en=prime_en,
    )
    hebrew = resolve_probe_via_hf_gloss_stub(
        str(lang.get("hebrew") or ""),
        "hebrew",
        rows,
        en_hint=en_hint,
        prime_en=prime_en,
    )
    explication = (
        f"[HYPO][HF_STUB] NSM prime '{prime_en}' — gloss-only greek→"
        f"{greek.get('lemma_script') or greek.get('resolution')} "
        f"(strongs={greek.get('strongs') or 'n/a'}); hebrew→"
        f"{hebrew.get('lemma_script') or hebrew.get('resolution')} "
        f"(strongs={hebrew.get('strongs') or 'n/a'})."
    )
    return {
        "schema": "deepnsm_hf_explication_stub_v1",
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
        "implementation_note": "Offline gloss-overlap stub — not DeepNSM HF 1B weights",
    }


__all__ = [
    "load_gematria_rows",
    "resolve_probe_via_hf_gloss_stub",
    "build_hf_stub_explication_record",
]
