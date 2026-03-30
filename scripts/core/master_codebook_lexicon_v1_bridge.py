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
_NAME_RE = re.compile(r"master_codebook_lexicon_v1_(\d+)_rows_latest\.json$")


def resolve_latest_codebook_path(
    out_dir: Path | None = None,
    explicit: Path | str | None = None,
) -> Path | None:
    if explicit is not None:
        p = Path(explicit).resolve()
        return p if p.is_file() else None
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
def _load_normalized_forms(path_str: str) -> frozenset[str]:
    path = Path(path_str)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "master_codebook_lexicon_v1":
        return frozenset()
    forms: set[str] = set()
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        nf = ent.get("normalized_form")
        if isinstance(nf, str) and nf.strip():
            forms.add(nf.strip().lower())
    return frozenset(forms)


def unicode_word_tokens(raw: str) -> set[str]:
    return {t.lower() for t in re.findall(r"\w+", raw, flags=re.UNICODE) if t}


def lexicon_hits_for_text(raw: str, path: Path) -> tuple[set[str], dict[str, Any]]:
    """Return (terms to add to must_keep, meta for route_info)."""
    if not path.is_file():
        return set(), {"status": "skipped", "reason": "file_missing", "path": str(path)}
    forms = _load_normalized_forms(str(path.resolve()))
    if not forms:
        return set(), {"status": "skipped", "reason": "empty_or_invalid_schema", "path": str(path.resolve())}
    toks = unicode_word_tokens(raw)
    hits = {h for h in (toks & forms) if len(h) >= 2}
    meta = {
        "status": "ok",
        "path": str(path.resolve()),
        "lexicon_term_count": len(forms),
        "hit_count": len(hits),
        "hits_sample": sorted(hits)[:24],
    }
    return hits, meta


def clear_codebook_cache() -> None:
    _load_normalized_forms.cache_clear()
