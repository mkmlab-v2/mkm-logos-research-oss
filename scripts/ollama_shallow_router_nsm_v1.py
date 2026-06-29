#!/usr/bin/env python3
"""NSM prime tag normalization + inference for Ollama shallow router (Layer A wire, B-track)."""

from __future__ import annotations

import re
from typing import Any

from scripts.nsm_41k_crosswalk_catalog_v1 import NSM_CROSSWALK_100

MAX_NSM_PRIME_TAGS = 3
_PRIME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

KNOWN_NSM_PRIMES: frozenset[str] = frozenset(
    str(row.get("prime_en") or "")
    for row in NSM_CROSSWALK_100
    if row.get("control") != "negative" and row.get("prime_en")
)

DOMAIN_DEFAULT_NSM_PRIMES: dict[str, list[str]] = {
    "logos": ["know", "words", "say"],
    "oracle": ["think", "know", "say"],
    "myeongni": ["when", "know", "happen"],
    "sasang": ["body", "feel", "good"],
    "infra": ["do", "happen", "move"],
    "devops": ["do", "happen", "if"],
    "design": ["see", "good", "say"],
}

_INPUT_KEYWORD_PRIMES: list[tuple[tuple[str, ...], str]] = [
    (("verse", "scripture", "bible", "성경", "구절", "logos"), "words"),
    (("고통", "pain", "suffer", "comfort"), "feel"),
    (("covenant", "언약", "promise"), "covenant"),
    (("hope", "소망", "stress"), "hope"),
    (("cleanup", "disk", "storage", "청소", "용량"), "do"),
    (("ci", "workflow", "deploy", "pipeline"), "do"),
    (("showroom", "ui", "pixel", "design", "copy"), "see"),
    (("명리", "myeongni", "사주"), "when"),
    (("사상", "sasang", "체질", "taeeum"), "body"),
    (("oracle", "tier2", "resume", "fusion"), "think"),
]


def normalize_nsm_prime_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        tag = str(item or "").strip().lower().replace("-", "_")
        if not tag or tag in seen:
            continue
        if tag not in KNOWN_NSM_PRIMES:
            continue
        if not _PRIME_RE.match(tag):
            continue
        out.append(tag)
        seen.add(tag)
        if len(out) >= MAX_NSM_PRIME_TAGS:
            break
    return out


def infer_nsm_prime_tags(domain_tag: str, input_text: str | None = None) -> list[str]:
    domain = str(domain_tag or "").strip().lower()
    tags: list[str] = []
    seen: set[str] = set()

    text = (input_text or "").lower()
    for keywords, prime in _INPUT_KEYWORD_PRIMES:
        if prime in seen:
            continue
        if any(kw in text for kw in keywords):
            if prime in KNOWN_NSM_PRIMES:
                tags.append(prime)
                seen.add(prime)

    for prime in DOMAIN_DEFAULT_NSM_PRIMES.get(domain, ["do", "know", "say"]):
        if prime in seen:
            continue
        if prime in KNOWN_NSM_PRIMES:
            tags.append(prime)
            seen.add(prime)
        if len(tags) >= MAX_NSM_PRIME_TAGS:
            break

    return tags[:MAX_NSM_PRIME_TAGS]


def enrich_shallow_output(
    parsed: dict[str, Any],
    *,
    input_text: str | None = None,
) -> dict[str, Any]:
    out = dict(parsed)
    existing = normalize_nsm_prime_tags(out.get("nsm_prime_tags"))
    if existing:
        out["nsm_prime_tags"] = existing
        return out
    domain = str(out.get("domain_tag") or "")
    out["nsm_prime_tags"] = infer_nsm_prime_tags(domain, input_text)
    return out


def nsm_wire_ok(parsed: dict[str, Any]) -> bool:
    tags = normalize_nsm_prime_tags(parsed.get("nsm_prime_tags"))
    return 1 <= len(tags) <= MAX_NSM_PRIME_TAGS
