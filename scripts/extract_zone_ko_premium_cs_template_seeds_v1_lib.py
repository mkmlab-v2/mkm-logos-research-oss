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
    return sum(1 for kw in keywords if kw in lower)


def must_keep_terms_for_snippet(snippet: str, keywords: list[str], *, min_terms: int = 1) -> list[str]:
    found = [kw for kw in keywords if kw in snippet or kw in snippet.lower()]
    if "███" in snippet and "███" not in found:
        found.append("███")
    if len(found) < min_terms:
        return found[: max(min_terms, len(found))]
    return found[:8]


def snippet_id_seed(snippet: str) -> str:
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()[:10]


def extract_from_jsonl(
    path: Path,
    *,
    shard: dict[str, Any],
    min_score: int = 1,
    max_rows: int = 50,
    skip_snippets: set[str] | None = None,
) -> list[dict[str, Any]]:
    skip = skip_snippets or set()
    keywords = shard_keywords(shard)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for obj in iter_jsonl_rows(path):
        labels = obj.get("labels") or []
        if labels and "premium_cs" not in " ".join(str(x) for x in labels).lower():
            if obj.get("domain_tag") != "customer-support-chat":
                continue
        for blob in row_text_blobs(obj):
            snippet = blob.strip()
            if snippet in skip or snippet in seen:
                continue
            if not looks_like_ko_premium_cs(snippet):
                continue
            score = score_snippet(snippet, keywords)
            if score < min_score:
                continue
            seen.add(snippet)
            template_id = f"kcs_p{snippet_id_seed(snippet)}"
            rows.append(
                {
                    "template_id": template_id,
                    "shard_id": str(shard.get("shard_id") or "zone_ko_premium_cs_v1"),
                    "language": "ko",
                    "snippet": snippet,
                    "must_keep_terms": must_keep_terms_for_snippet(snippet, keywords),
                    "extract_score": score,
                    "source_jsonl": path.name,
                }
            )
            if len(rows) >= max_rows:
                return rows
    return rows
