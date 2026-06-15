"""Extract zone_h_en_business formal template seeds from JSONL corpora (B-track PoC).

research_only · does not auto-merge into production catalog.
Separate vertical from zone_f_code (coding) and wtt_premium_cs (Korean CS shortcap).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

TEXT_KEYS = ("snippet", "text", "raw_text", "content", "body", "canonical")
PARA_SPLIT = re.compile(r"\n\s*\n+")
EN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def load_shard(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def shard_keywords(shard: dict[str, Any]) -> list[str]:
    keys = list(shard.get("routing_keywords") or [])
    keys.extend(shard.get("must_keep_hard_terms") or [])
    keys.extend(shard.get("must_keep_soft_terms") or [])
    return sorted({str(k).lower() for k in keys if k})


def iter_jsonl_rows(path: Path) -> Iterator[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def row_text_blobs(obj: dict[str, Any]) -> list[str]:
    blobs: list[str] = []
    for key in TEXT_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            blobs.append(val)
    return blobs


def english_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    hangul = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
    denom = letters + hangul
    if denom == 0:
        return 0.0
    return letters / denom


def looks_like_en_business_prose(text: str, *, min_en_ratio: float = 0.85) -> bool:
    stripped = text.strip()
    if len(stripped) < 60:
        return False
    if english_ratio(stripped) < min_en_ratio:
        return False
    lower = stripped.lower()
    markers = ("dear ", "subject:", "regards", "sincerely", "invoice", "payment", "contract", "attached", "pursuant", "notice:", "purchase order")
    return sum(1 for m in markers if m in lower) >= 1


def score_snippet(snippet: str, keywords: list[str]) -> int:
    lower = snippet.lower()
    return sum(1 for kw in keywords if kw in lower)


def must_keep_terms_for_snippet(snippet: str, keywords: list[str], *, min_terms: int = 2) -> list[str]:
    lower = snippet.lower()
    found = [kw for kw in keywords if kw in lower]
    if len(found) < min_terms:
        return []
    return found[:8]


def normalize_snippet(snippet: str) -> str:
    return snippet.replace("\r\n", "\n").strip()


def snippet_hash(snippet: str) -> str:
    return hashlib.sha256(normalize_snippet(snippet).encode("utf-8")).hexdigest()


def extract_paragraph_candidates(text: str) -> list[str]:
    blocks = [normalize_snippet(b) for b in PARA_SPLIT.split(text) if b.strip()]
    if not blocks and text.strip():
        blocks = [normalize_snippet(text)]
    out: list[str] = []
    for block in blocks:
        if looks_like_en_business_prose(block):
            out.append(block)
    if looks_like_en_business_prose(text) and not out:
        out.append(normalize_snippet(text))
    return out


def extract_candidates_from_text(
    text: str,
    *,
    keywords: list[str],
    min_score: int = 2,
    max_chars: int = 2500,
) -> list[str]:
    out: list[str] = []
    for snippet in extract_paragraph_candidates(text):
        if len(snippet) > max_chars:
            continue
        if score_snippet(snippet, keywords) < min_score:
            continue
        if not must_keep_terms_for_snippet(snippet, keywords):
            continue
        out.append(snippet)
    return out


def extract_seeds_from_row(
    obj: dict[str, Any],
    *,
    keywords: list[str],
    source_row_id: str | None = None,
    min_score: int = 2,
) -> list[dict[str, Any]]:
    row_id = source_row_id or str(obj.get("id") or obj.get("case_id") or "")
    domain = str(obj.get("domain_tag") or "")
    if domain and "en-business" not in domain and domain != "en_business_formal":
        if "customer-support" in domain or "cs" in domain:
            return []
    seeds: list[dict[str, Any]] = []
    for blob in row_text_blobs(obj):
        for snippet in extract_candidates_from_text(blob, keywords=keywords, min_score=min_score):
            terms = must_keep_terms_for_snippet(snippet, keywords)
            seeds.append(
                {
                    "snippet": snippet,
                    "snippet_sha256": snippet_hash(snippet),
                    "language": "en",
                    "must_keep_terms": terms,
                    "source_row_id": row_id,
                    "source_keys": [k for k in TEXT_KEYS if isinstance(obj.get(k), str)],
                }
            )
    return seeds


def dedupe_seeds(seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for seed in seeds:
        h = str(seed.get("snippet_sha256") or snippet_hash(str(seed.get("snippet") or "")))
        if h in seen:
            continue
        seen.add(h)
        seed["snippet_sha256"] = h
        out.append(seed)
    return out


def filter_existing_catalog(
    seeds: list[dict[str, Any]],
    existing_snippets: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    novel: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    existing_norm = {normalize_snippet(s) for s in existing_snippets}
    for seed in seeds:
        snippet = normalize_snippet(str(seed.get("snippet") or ""))
        if snippet in existing_norm:
            skipped.append({**seed, "skip_reason": "already_in_catalog"})
        else:
            novel.append(seed)
    return novel, skipped


def assign_prospect_template_ids(
    seeds: list[dict[str, Any]],
    *,
    prefix: str = "eb_p",
    start_index: int = 1,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds, start=start_index):
        rows.append(
            {
                "template_id": f"{prefix}{i:03d}",
                "shard_id": "zone_h_en_business_v1",
                "language": "en",
                "snippet": seed["snippet"],
                "must_keep_terms": seed.get("must_keep_terms") or [],
                "prospect": True,
                "source_row_id": seed.get("source_row_id"),
                "snippet_sha256": seed.get("snippet_sha256"),
            }
        )
    return rows


def extract_from_jsonl(
    path: Path,
    *,
    shard: dict[str, Any],
    existing_snippets: set[str] | None = None,
    min_score: int = 2,
) -> dict[str, Any]:
    keywords = shard_keywords(shard)
    raw_seeds: list[dict[str, Any]] = []
    rows_scanned = 0
    for obj in iter_jsonl_rows(path):
        rows_scanned += 1
        raw_seeds.extend(extract_seeds_from_row(obj, keywords=keywords, min_score=min_score))
    deduped = dedupe_seeds(raw_seeds)
    existing = existing_snippets or set()
    novel, skipped = filter_existing_catalog(deduped, existing)
    prospect_rows = assign_prospect_template_ids(novel)
    return {
        "input_jsonl": path.as_posix(),
        "rows_scanned": rows_scanned,
        "candidates_raw": len(raw_seeds),
        "candidates_deduped": len(deduped),
        "candidates_novel": len(novel),
        "candidates_skipped_existing": len(skipped),
        "prospect_rows": prospect_rows,
        "skipped": skipped,
    }
