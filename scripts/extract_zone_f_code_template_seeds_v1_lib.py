"""Extract zone_f_code template seed candidates from customer JSONL corpora (B-track PoC).

research_only · does not auto-merge into production catalog.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

from scripts.zone_f_code_multilang_extract_v1_lib import (  # noqa: E402
    detect_fence_lang,
    infer_snippet_language,
    looks_like_code_snippet as looks_like_multilang_snippet,
)

FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
CODE_LINE_START = re.compile(
    r"^\s*(def |class |import |from |async def |@app\.|@pytest|try:|except |if __name__)",
    re.MULTILINE,
)
TEXT_KEYS = ("snippet", "text", "raw_text", "content", "body", "canonical")


def load_zone_f_code_shard(path: Path) -> dict[str, Any]:
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


def _messages_text(obj: dict[str, Any]) -> list[str]:
    out: list[str] = []
    messages = obj.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    out.append(content)
    return out


def row_text_blobs(obj: dict[str, Any]) -> list[str]:
    blobs: list[str] = []
    for key in TEXT_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            blobs.append(val)
    blobs.extend(_messages_text(obj))
    return blobs


def extract_fenced_code_blocks(text: str) -> list[str]:
    blocks = [m.group(1).strip() for m in FENCE_RE.finditer(text) if m.group(1).strip()]
    return blocks


def looks_like_code_snippet(text: str, *, lang: str | None = None) -> bool:
    return looks_like_multilang_snippet(text, lang=lang)


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


def extract_candidates_from_text(
    text: str,
    *,
    keywords: list[str],
    min_score: int = 2,
    min_lines: int = 2,
    max_chars: int = 2000,
) -> list[str]:
    candidates: list[str] = []
    for block in extract_fenced_code_blocks(text):
        if looks_like_code_snippet(block):
            candidates.append(normalize_snippet(block))
    if looks_like_code_snippet(text) and not extract_fenced_code_blocks(text):
        candidates.append(normalize_snippet(text))
    out: list[str] = []
    fence_lang = detect_fence_lang(text)
    for snippet in candidates:
        if not looks_like_code_snippet(snippet, lang=fence_lang):
            continue
        if snippet.count("\n") + 1 < min_lines and len(snippet) < 40:
            continue
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
    seeds: list[dict[str, Any]] = []
    for blob in row_text_blobs(obj):
        fence_lang = detect_fence_lang(blob)
        for snippet in extract_candidates_from_text(blob, keywords=keywords, min_score=min_score):
            lang = infer_snippet_language(snippet, blob)
            terms = must_keep_terms_for_snippet(snippet, keywords)
            seeds.append(
                {
                    "snippet": snippet,
                    "snippet_sha256": snippet_hash(snippet),
                    "language": lang,
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
    prefix: str = "zf_p",
    start_index: int = 1,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds, start=start_index):
        rows.append(
            {
                "template_id": f"{prefix}{i:03d}",
                "shard_id": "zone_f_code",
                "language": seed.get("language") or "python",
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
