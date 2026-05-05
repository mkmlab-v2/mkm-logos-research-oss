# -*- coding: utf-8 -*-
"""Recommend normalized external Myeongri references for advanced answers.

Reads docs/final/artifacts/myeongri_external_reference_catalog_latest.json and returns
top-N candidates by profile/tag match + verification level.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "docs" / "final" / "artifacts" / "myeongri_external_reference_catalog_latest.json"

PROFILE_TAGS: dict[str, list[str]] = {
    "general": ["quantification", "saju", "myeongri"],
    "daewoon": ["daewoon", "calculation-method", "calendar-correction"],
    "ten-gods": ["ten-gods", "quantification"],
    "yongsin": ["yongsin", "quantification", "method-limits"],
    "career": ["career-guidance", "ml", "four-pillars"],
    "llm-benchmark": ["benchmark", "symbolic-reasoning", "bazi-llm", "temporal-composition"],
    "landscape": ["landscape", "competitor-pattern", "rag-pattern"],
}

VERIFICATION_WEIGHT = {
    "A_verified_primary": 3.0,
    "B_verified_metadata": 2.0,
    "C_unverified_candidate": 1.0,
}


def _safe_tags(entry: dict[str, Any]) -> set[str]:
    raw = entry.get("normalization_tags") or []
    return {str(x).strip().lower() for x in raw if str(x).strip()}


def _tokenize(s: str) -> set[str]:
    return {t for t in s.lower().replace("_", " ").replace("-", " ").split() if t}


def recommend_entries(
    *,
    catalog: dict[str, Any],
    profile: str,
    extra_tags: list[str] | None = None,
    query: str = "",
    top_n: int = 5,
) -> list[dict[str, Any]]:
    entries = catalog.get("entries") or []
    base_tags = set(PROFILE_TAGS.get(profile, []))
    user_tags = {t.strip().lower() for t in (extra_tags or []) if t.strip()}
    wanted_tags = base_tags | user_tags
    query_tokens = _tokenize(query)

    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    for e in entries:
        tags = _safe_tags(e)
        matched_tags = sorted(wanted_tags & tags)
        score = float(len(matched_tags))
        score += VERIFICATION_WEIGHT.get(str(e.get("verification_level", "")), 0.0)

        # Query-aware small boost from title/use text
        query_matches: list[str] = []
        if query_tokens:
            hay = _tokenize(f"{e.get('title', '')} {e.get('recommended_use', '')}")
            qhit = sorted(query_tokens & hay)
            query_matches = qhit
            score += 0.25 * len(qhit)

        # Keep weakly relevant but stable recommendations if profile is broad.
        if wanted_tags and not matched_tags and profile not in ("general", "landscape"):
            continue

        row = dict(e)
        row["matched_tags"] = matched_tags
        row["query_hits"] = query_matches
        row["score"] = round(score, 3)
        scored.append((score, row, matched_tags))

    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [row for _, row, _ in scored[: max(1, top_n)]]


def build_payload(
    *,
    catalog_path: Path,
    profile: str,
    extra_tags: list[str],
    query: str,
    top_n: int,
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "myeongri_external_reference_recommendation_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog_path": str(catalog_path.as_posix()),
        "profile": profile,
        "extra_tags": extra_tags,
        "query": query,
        "top_n": top_n,
        "rag_sources_used_suggested": [r.get("source_locator") for r in recommendations],
        "recommendations": recommendations,
        "policy_note": "B-track enrichment only. Re-validate any claim with CONSTITUTION + runnable scripts + artifacts before promotion.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--profile", default="general", choices=tuple(PROFILE_TAGS.keys()))
    ap.add_argument("--tag", action="append", default=[], help="Extra normalization tag (repeatable)")
    ap.add_argument("--query", default="", help="Free-text question/topic hint")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--out", type=Path, help="Optional JSON output path")
    args = ap.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    recs = recommend_entries(
        catalog=catalog,
        profile=args.profile,
        extra_tags=list(args.tag),
        query=args.query,
        top_n=args.top_n,
    )
    payload = build_payload(
        catalog_path=args.catalog,
        profile=args.profile,
        extra_tags=list(args.tag),
        query=args.query,
        top_n=args.top_n,
        recommendations=recs,
    )

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
