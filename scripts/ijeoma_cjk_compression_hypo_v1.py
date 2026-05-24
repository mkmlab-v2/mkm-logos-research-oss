#!/usr/bin/env python3
"""[HYPO] CJK phrase → atom-id substitution compression (B-track; not Track A)."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

MARKER_STRATEGIES = frozenset({"pua", "ascii_compact", "atom_id", "o200k_tight"})
SHORTER_BY_VALUES = frozenset({"tokens", "chars", "o200k"})
DEFAULT_MARKER_STRATEGY = "ascii_compact"
DEFAULT_SHORTER_BY = "tokens"
_BILLING_MODE_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_ijeoma_cjk_billing_mode() -> bool:
    """Env MKM_IJEOMA_CJK_BILLING_MODE=1 forces o200k_tight on hook (B-track billing research)."""
    v = (os.environ.get("MKM_IJEOMA_CJK_BILLING_MODE") or "").strip().lower()
    return v in _BILLING_MODE_TRUTHY

_CJK_RUN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")


def _tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def _marker_for_index_pua(idx: int) -> str:
    """Unique PUA marker — single-char pool (BMP PUA U+E000..U+F8FF, 6400 slots) then 2-char."""
    base = 0xE000
    pua_span = 0xF8FF - base + 1  # 6400
    if idx < pua_span:
        return chr(base + idx)
    rem = idx - pua_span
    return chr(base + (rem // pua_span) % pua_span) + chr(base + (rem % pua_span))


def _marker_for_index(idx: int) -> str:
    return _marker_for_index_pua(idx)


def _marker_ascii_compact(idx: int) -> str:
    """B-track o200k-friendly marker: m + 4 base36 digits (20k+ unique)."""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    n = max(0, idx)
    chars: list[str] = []
    for _ in range(4):
        chars.append(alphabet[n % 36])
        n //= 36
    return "m" + "".join(reversed(chars))


@lru_cache(maxsize=1)
def _o200k_tight_marker_pool(max_needed: int = 25000) -> tuple[str, ...]:
    """Markers with o200k_base length <= 2 (singles, then 1-token pairs, then 1/2-token triples)."""
    try:
        import tiktoken  # noqa: WPS433
    except ImportError:
        return tuple()
    enc = tiktoken.get_encoding("o200k_base")
    alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    pool: list[str] = []
    for a in alph:
        if len(enc.encode(a)) == 1:
            pool.append(a)
    for a in alph:
        for b in alph:
            s = a + b
            if len(enc.encode(s)) == 1:
                pool.append(s)
    triple_one: list[str] = []
    triple_two: list[str] = []
    for a in alph:
        for b in alph:
            for c in alph:
                s = a + b + c
                n = len(enc.encode(s))
                if n == 1:
                    triple_one.append(s)
                elif n == 2:
                    triple_two.append(s)
                if len(pool) + len(triple_one) + len(triple_two) >= max_needed:
                    break
            if len(pool) + len(triple_one) + len(triple_two) >= max_needed:
                break
        if len(pool) + len(triple_one) + len(triple_two) >= max_needed:
            break
    pool.extend(triple_one)
    pool.extend(triple_two)
    return tuple(pool[:max_needed])


@lru_cache(maxsize=1)
def _o200k_encoder() -> Any | None:
    try:
        import tiktoken  # noqa: WPS433
    except ImportError:
        return None
    return tiktoken.get_encoding("o200k_base")


def _o200k_token_len(text: str) -> int:
    enc = _o200k_encoder()
    if enc is None:
        return _tokens(text)
    return len(enc.encode(text))


def _resolve_marker(ent: dict[str, Any], idx: int, marker_strategy: str) -> str:
    if marker_strategy == "ascii_compact":
        return _marker_ascii_compact(idx)
    if marker_strategy == "o200k_tight":
        pool = _o200k_tight_marker_pool()
        if pool and idx < len(pool):
            return pool[idx]
        return _marker_ascii_compact(idx)
    if marker_strategy == "atom_id":
        aid = ent.get("atom_id")
        if isinstance(aid, str) and aid:
            return aid
    return _marker_for_index_pua(idx)


@lru_cache(maxsize=16)
def _load_lexicon_maps(path_str: str, marker_strategy: str = "pua") -> tuple[dict[str, str], dict[str, str]]:
    doc = json.loads(Path(path_str).read_text(encoding="utf-8"))
    form_to_marker: dict[str, str] = {}
    marker_to_form: dict[str, str] = {}
    idx = 0
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        form = ent.get("normalized_form")
        if not isinstance(form, str) or not form:
            continue
        if form in form_to_marker:
            continue
        mark = _resolve_marker(ent, idx, marker_strategy)
        idx += 1
        form_to_marker[form] = mark
        marker_to_form[mark] = form
    return form_to_marker, marker_to_form


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RUN.search(text))


def resolve_marker_strategy(
    explicit: str | None = None,
    case: dict[str, Any] | None = None,
) -> str:
    """B-track marker: per-case > explicit > billing mode (o200k_tight) > env > ascii_compact."""
    if case is not None:
        from_case = case.get("ijeoma_cjk_marker_strategy")
        if isinstance(from_case, str) and from_case in MARKER_STRATEGIES:
            return from_case
    if explicit and explicit in MARKER_STRATEGIES:
        return explicit
    if is_ijeoma_cjk_billing_mode():
        return "o200k_tight"
    env = (os.environ.get("MKM_IJEOMA_CJK_MARKER_STRATEGY") or "").strip().lower()
    if env in MARKER_STRATEGIES:
        return env
    return DEFAULT_MARKER_STRATEGY


def resolve_shorter_by(
    explicit: str | None = None,
    case: dict[str, Any] | None = None,
) -> str:
    """Replacement gate: per-case > kwarg > env MKM_IJEOMA_CJK_SHORTER_BY > tokens."""
    if case is not None:
        from_case = case.get("ijeoma_cjk_shorter_by")
        if isinstance(from_case, str) and from_case in SHORTER_BY_VALUES:
            return from_case
    if explicit and explicit in SHORTER_BY_VALUES:
        return explicit
    env = (os.environ.get("MKM_IJEOMA_CJK_SHORTER_BY") or "").strip().lower()
    if env in SHORTER_BY_VALUES:
        return env
    return DEFAULT_SHORTER_BY


def default_hypo_lexicon_path() -> Path:
    return Path(__file__).resolve().parent.parent / (
        "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
    )


def compress_ijeoma_cjk_substitution(
    raw: str,
    lexicon_path: Path,
    *,
    only_if_shorter: bool = True,
    shorter_by: str = "tokens",
    marker_strategy: str = "pua",
) -> tuple[str, dict[str, Any]]:
    """Greedy longest-match phrase replacement (B-track markers).

    marker_strategy: ``pua`` | ``ascii_compact`` | ``o200k_tight`` | ``atom_id``.
    shorter_by: ``tokens`` (eval proxy) | ``chars`` | ``o200k`` (tiktoken o200k_base gate).
    """
    form_to_marker, _ = _load_lexicon_maps(str(lexicon_path.resolve()), marker_strategy)
    forms = sorted(form_to_marker.keys(), key=len, reverse=True)
    out: list[str] = []
    i = 0
    replacements = 0
    skipped_longer_marker = 0
    while i < len(raw):
        hit = False
        for form in forms:
            n = len(form)
            if n and raw[i : i + n] == form:
                marker = form_to_marker[form]
                if only_if_shorter:
                    if shorter_by == "chars":
                        no_gain = len(marker) >= n
                    elif shorter_by == "o200k":
                        no_gain = _o200k_token_len(marker) >= _o200k_token_len(form)
                    else:
                        no_gain = _tokens(marker) >= _tokens(form)
                    if no_gain:
                        skipped_longer_marker += 1
                        break
                out.append(marker)
                i += n
                replacements += 1
                hit = True
                break
        if not hit:
            out.append(raw[i])
            i += 1
    compressed = "".join(out)
    raw_t = _tokens(raw)
    comp_t = _tokens(compressed)
    saving = 1.0 - (comp_t / raw_t) if raw_t else 0.0
    return compressed, {
        "replacements": replacements,
        "skipped_longer_marker": skipped_longer_marker,
        "raw_tokens_proxy": raw_t,
        "compressed_tokens_proxy": comp_t,
        "token_saving_rate_proxy": round(saving, 4),
        "marker_strategy": marker_strategy,
        "shorter_by": shorter_by,
        "billing_mode": is_ijeoma_cjk_billing_mode(),
    }


def expand_ijeoma_cjk_substitution(
    compressed: str,
    lexicon_path: Path,
    *,
    marker_strategy: str = "pua",
) -> str:
    """Expand markers back to normalized_form (strategy must match compress)."""
    _, marker_to_form = _load_lexicon_maps(str(lexicon_path.resolve()), marker_strategy)
    out: list[str] = []
    i = 0
    marks = sorted(marker_to_form.keys(), key=len, reverse=True)
    while i < len(compressed):
        matched = False
        for mark in marks:
            if compressed.startswith(mark, i):
                out.append(marker_to_form[mark])
                i += len(mark)
                matched = True
                break
        if not matched:
            out.append(compressed[i])
            i += 1
    return "".join(out)
