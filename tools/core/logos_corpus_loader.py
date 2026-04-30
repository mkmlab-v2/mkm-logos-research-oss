from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Sequence, Tuple


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_hebrew_greek_jsonl(root: Path | None = None) -> Path:
    base = root or _workspace_root()
    primary = base / "data" / "logos" / "bible_original_hebrew_greek.jsonl"
    if primary.is_file():
        return primary
    # Fallback for local/dev branches where canonical corpus is not tracked.
    fallback = base / "tests" / "fixtures" / "logos_mini.jsonl"
    return fallback


def default_canon_plus_manuscripts(root: Path | None = None) -> list[Path]:
    base = root or _workspace_root()
    canon = default_hebrew_greek_jsonl(base)
    manuscripts = [
        base / "data" / "logos" / "manuscripts" / "dss_noncanon_and_variants_v1.0.0.jsonl",
        base / "data" / "logos" / "manuscripts" / "apocrypha_deuterocanon_v1.0.0.jsonl",
    ]
    out = [canon]
    out.extend([p for p in manuscripts if p.is_file()])
    return out


def verse_logos_text(rec: dict[str, Any]) -> str:
    # Prefer explicit normalized text fields first.
    for k in ("logos_text", "text", "content", "verse_text"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Fallback for fixture/source rows where language fields are split.
    h = str(rec.get("text_hebrew") or "").strip()
    g = str(rec.get("text_greek") or "").strip()
    if h and g:
        return f"{h} {g}".strip()
    if h:
        return h
    if g:
        return g
    return ""


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def iter_hebrew_greek_jsonl(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    count = 0
    for rec in _iter_jsonl(path):
        yield rec
        count += 1
        if limit is not None and count >= int(limit):
            break


def iter_union_jsonl(
    paths: Sequence[Path], global_limit: int | None = None
) -> Iterator[Tuple[Path, dict[str, Any]]]:
    count = 0
    for p in paths:
        for rec in _iter_jsonl(p):
            yield p, rec
            count += 1
            if global_limit is not None and count >= int(global_limit):
                return


def load_verse_slice(path: Path, limit: int = 10) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    for i, rec in enumerate(iter_hebrew_greek_jsonl(path, limit=limit), start=1):
        vid = str(rec.get("verse_id") or rec.get("source_ref") or f"row_{i}")
        txt = verse_logos_text(rec)
        if not txt:
            continue
        ids.append(vid)
        texts.append(txt)
    return ids, texts
