# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.85, K:0.55, M:0.5}
# Balance: 88
# Purpose: Resolve Master Codebook Lexicon V1 export path and match tokens for compression must_keep.
# Keywords: lexicon, codebook, compression, bridge
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DIR = _ROOT / "reports" / "constitution" / "btrack_pilot"
_POINTER = _DEFAULT_DIR / "master_codebook_bench_lexicon_pointer_v1_latest.json"
_NAME_RE = re.compile(r"master_codebook_lexicon_v1_(\d+)_rows_latest\.json$")


def _production_ssot_from_pointer() -> Path | None:
    if not _POINTER.is_file():
        return None
    try:
        doc = json.loads(_POINTER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    prod = doc.get("production_ssot")
    if not isinstance(prod, dict):
        return None
    raw = prod.get("path")
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw.strip())
    if not p.is_absolute():
        p = (_ROOT / p).resolve()
    return p if p.is_file() else None


def resolve_latest_codebook_path(
    out_dir: Path | None = None,
    explicit: Path | str | None = None,
) -> Path | None:
    if explicit is not None:
        p = Path(explicit).resolve()
        return p if p.is_file() else None
    from_pointer = _production_ssot_from_pointer()
    if from_pointer is not None:
        return from_pointer
    base = out_dir or _DEFAULT_DIR
    if not base.is_dir():
        return None
    best: Path | None = None
    best_n = -1
    for p in base.glob("master_codebook_lexicon_v1_*_rows_latest.json"):
        m = _NAME_RE.search(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n > best_n:
            best_n, best = n, p
    return best


@lru_cache(maxsize=8)
def _load_lexicon_index(path_str: str) -> tuple[frozenset[str], dict[str, str]]:
    """Return (normalized_forms, form_lower -> atom_id)."""
    path = Path(path_str)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        return frozenset(), {}
    forms: set[str] = set()
    form_to_atom: dict[str, str] = {}
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        nf = ent.get("normalized_form")
        aid = ent.get("atom_id")
        if not isinstance(nf, str) or not nf.strip():
            continue
        key = nf.strip().lower()
        forms.add(key)
        if isinstance(aid, str) and aid.strip() and key not in form_to_atom:
            form_to_atom[key] = aid.strip()
    return frozenset(forms), form_to_atom


@lru_cache(maxsize=8)
def _load_normalized_forms(path_str: str) -> frozenset[str]:
    forms, _ = _load_lexicon_index(path_str)
    return forms


def unicode_word_tokens(raw: str) -> set[str]:
    return {t.lower() for t in re.findall(r"\w+", raw, flags=re.UNICODE) if t}


_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")


def cjk_bigram_tokens(raw: str) -> set[str]:
    """Adjacent han/CJK bigrams inside each ideographic run (B-track PoC helper)."""
    out: set[str] = set()
    for run in _CJK_RUN_RE.findall(raw):
        if len(run) < 2:
            continue
        for i in range(len(run) - 1):
            out.add(run[i : i + 2].lower())
    return out


def lexicon_atom_sequence_for_text(
    raw: str,
    path: Path,
    *,
    max_atoms: int = 48,
    min_token_len: int = 2,
) -> tuple[list[str], dict[str, Any]]:
    """Ordered atom_id list for tokens that match lexicon normalized_form (appearance order)."""
    if not path.is_file():
        return [], {"status": "skipped", "reason": "file_missing", "path": str(path)}
    forms, form_to_atom = _load_lexicon_index(str(path.resolve()))
    if not forms:
        return [], {"status": "skipped", "reason": "empty_or_invalid_schema", "path": str(path.resolve())}
    sequence: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"\w+", raw, flags=re.UNICODE):
        tok = match.group(0).lower()
        if len(tok) < min_token_len:
            continue
        if tok not in form_to_atom or tok in seen:
            continue
        seen.add(tok)
        sequence.append(form_to_atom[tok])
        if len(sequence) >= max_atoms:
            break
    meta = {
        "status": "ok",
        "path": str(path.resolve()),
        "lexicon_term_count": len(forms),
        "atom_id_count": len(sequence),
        "atom_id_sequence_sample": sequence[:12],
    }
    return sequence, meta


def lexicon_hits_for_text(
    raw: str,
    path: Path,
    *,
    min_token_len: int = 2,
    include_cjk_bigrams: bool = False,
) -> tuple[set[str], dict[str, Any]]:
    """Return (terms to add to must_keep, meta for route_info)."""
    if not path.is_file():
        return set(), {"status": "skipped", "reason": "file_missing", "path": str(path)}
    forms = _load_normalized_forms(str(path.resolve()))
    if not forms:
        return set(), {"status": "skipped", "reason": "empty_or_invalid_schema", "path": str(path.resolve())}
    toks = unicode_word_tokens(raw)
    if include_cjk_bigrams:
        toks = toks | cjk_bigram_tokens(raw)
    hits = {h for h in (toks & forms) if len(h) >= min_token_len}
    meta = {
        "status": "ok",
        "path": str(path.resolve()),
        "lexicon_term_count": len(forms),
        "hit_count": len(hits),
        "min_token_len": min_token_len,
        "include_cjk_bigrams": include_cjk_bigrams,
        "hits_sample": sorted(hits)[:24],
    }
    return hits, meta


@lru_cache(maxsize=8)
def _load_atom_id_to_form(path_str: str) -> dict[str, str]:
    """Return atom_id -> normalized_form (first entry wins)."""
    path = Path(path_str)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        return {}
    out: dict[str, str] = {}
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        aid = ent.get("atom_id")
        nf = ent.get("normalized_form")
        if isinstance(aid, str) and aid.strip() and isinstance(nf, str) and nf.strip():
            out.setdefault(aid.strip(), nf.strip())
    return out


def gloss_rows_for_atom_ids(
    atom_ids: list[str],
    path: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Human-readable gloss per atom_id (research decoder; not L1 inverse)."""
    if not path.is_file():
        return [], {"status": "skipped", "reason": "file_missing"}
    idx = _load_atom_id_to_form(str(path.resolve()))
    rows: list[dict[str, str]] = []
    for aid in atom_ids:
        key = str(aid)
        rows.append(
            {
                "atom_id": key,
                "gloss": idx.get(key, ""),
                "known": key in idx,
            }
        )
    known_n = sum(1 for r in rows if r.get("known"))
    return rows, {
        "status": "ok",
        "path": str(path.resolve()),
        "atom_id_count": len(rows),
        "known_gloss_count": known_n,
        "research_only": True,
    }


def clear_codebook_cache() -> None:
    _load_normalized_forms.cache_clear()
    _load_lexicon_index.cache_clear()
    _load_atom_id_to_form.cache_clear()
