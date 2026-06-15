"""Extract zone_ko_premium_cs template seeds from masked Korean CS JSONL (B-track PoC)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

TEXT_KEYS = ("snippet", "text", "raw_text", "content", "body", "canonical")
MASK_RE = re.compile(r"█|\*{2,}")


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
    turns = obj.get("turns")
    if isinstance(turns, list):
        joined = " ".join(str(t.get("text") or "") for t in turns if isinstance(t, dict))
        if joined.strip():
            blobs.append(joined)
    return blobs


def hangul_ratio(text: str) -> float:
    if not text:
        return 0.0
    hangul = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
    letters = sum(1 for ch in text if ch.isalpha())
    denom = max(1, hangul + letters)
    return hangul / denom


def has_mask_token(text: str) -> bool:
    return bool(MASK_RE.search(text))


def looks_like_ko_premium_cs(text: str, *, min_hangul_ratio: float = 0.35) -> bool:
    stripped = text.strip()
    if len(stripped) < 12:
        return False
    if hangul_ratio(stripped) < min_hangul_ratio:
        return False
    if not has_mask_token(stripped):
        return False
    lower = stripped.lower()
    markers = ("환불", "프리미엄", "고객", "vip", "주문", "상담", "구독", "배송", "청구서", "티켓", "과금")
    return sum(1 for m in markers if m in lower) >= 1


def score_snippet(snippet: str, keywords: list[str]) -> int:
    lower = snippet.lower()
    return sum(1 for kw in keywords if kw in snippet or kw in lower)


def must_keep_terms_for_snippet(snippet: str, keywords: list[str], *, min_terms: int = 1) -> list[str]:
    found = [kw for kw in keywords if kw in snippet or kw in snippet.lower()]
    if "███" in snippet and "███" not in found:
        found.append("███")
    if len(found) < min_terms:
        return found[: max(min_terms, len(found))]
    return found[:8]


def normalize_snippet(snippet: str) -> str:
    return snippet.replace("\r\n", "\n").strip()


def snippet_hash(snippet: str) -> str:
    return hashlib.sha256(normalize_snippet(snippet).encode("utf-8")).hexdigest()


def row_allowed_for_ko_cs(obj: dict[str, Any]) -> bool:
    labels = obj.get("labels") or []
    label_blob = " ".join(str(x) for x in labels).lower()
    if labels and "premium_cs" not in label_blob:
        return obj.get("domain_tag") == "customer-support-chat"
    tenant = str(obj.get("tenant_id") or "")
    if tenant and "premium-cs" in tenant:
        return True
    return obj.get("domain_tag") == "customer-support-chat" or not labels


def extract_seeds_from_row(
    obj: dict[str, Any],
    *,
    keywords: list[str],
    source_row_id: str | None = None,
    min_score: int = 1,
) -> list[dict[str, Any]]:
    if not row_allowed_for_ko_cs(obj):
        return []
    row_id = source_row_id or str(obj.get("id") or obj.get("session_id") or "")
    seeds: list[dict[str, Any]] = []
    for blob in row_text_blobs(obj):
        snippet = normalize_snippet(blob)
        if not looks_like_ko_premium_cs(snippet):
            continue
        score = score_snippet(snippet, keywords)
        if score < min_score:
            continue
        seeds.append(
            {
                "snippet": snippet,
                "snippet_sha256": snippet_hash(snippet),
                "language": "ko",
                "must_keep_terms": must_keep_terms_for_snippet(snippet, keywords),
                "source_row_id": row_id,
                "extract_score": score,
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
    prefix: str = "kcs_p",
    start_index: int = 1,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds, start=start_index):
        rows.append(
            {
                "template_id": f"{prefix}{i:03d}",
                "shard_id": "zone_ko_premium_cs_v1",
                "language": "ko",
                "snippet": seed["snippet"],
                "must_keep_terms": seed.get("must_keep_terms") or [],
                "prospect": True,
                "source_row_id": seed.get("source_row_id"),
                "snippet_sha256": seed.get("snippet_sha256"),
                "extract_score": seed.get("extract_score"),
            }
        )
    return rows


def extract_from_jsonl(
    path: Path,
    *,
    shard: dict[str, Any],
    existing_snippets: set[str] | None = None,
    min_score: int = 1,
    max_rows: int = 50,
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
    prospect_rows = assign_prospect_template_ids(novel[:max_rows])
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
