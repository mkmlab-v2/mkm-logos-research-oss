"""Evaluate zone_ko_premium_cs template catalog wire coverage across JSONL corpora (B-track).

research_only · CS_MASK wire family · separate from BIZ_MASK and ZF_MASK.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.compression_ko_premium_cs_deep_pack_v1_lib import (
    load_template_catalog,
    resolve_template_match,
)
from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import (
    extract_seeds_from_row,
    iter_jsonl_rows,
    load_shard,
    shard_keywords,
)


def evaluate_corpus_snippet_coverage(
    path: Path,
    *,
    shard: dict[str, Any],
    catalog_rows: list[dict[str, Any]],
    min_score: int = 1,
) -> dict[str, Any]:
    keywords = shard_keywords(shard)
    rows_scanned = 0
    rows_with_candidates = 0
    snippet_candidates_total = 0
    wire_match_count = 0
    wire_miss_count = 0
    misses: list[dict[str, Any]] = []

    seen_snippets: set[str] = set()
    non_canonical_skipped = 0

    for obj in iter_jsonl_rows(path):
        rows_scanned += 1
        seeds = extract_seeds_from_row(obj, keywords=keywords, min_score=min_score)
        snippets = [str(s.get("snippet") or "") for s in seeds if s.get("snippet")]
        if not snippets:
            continue
        rows_with_candidates += 1
        for snippet in snippets:
            if "███" not in snippet:
                non_canonical_skipped += 1
                continue
            norm = snippet.strip()
            if norm in seen_snippets:
                continue
            seen_snippets.add(norm)
            snippet_candidates_total += 1
            resolved = resolve_template_match(snippet, catalog_rows)
            if resolved:
                wire_match_count += 1
            else:
                wire_miss_count += 1
                if len(misses) < 12:
                    misses.append(
                        {
                            "row_id": str(obj.get("id") or obj.get("session_id") or ""),
                            "snippet_preview": snippet[:120],
                            "reason": "no_exact_catalog_snippet_match",
                        }
                    )

    denom = snippet_candidates_total
    return {
        "input_jsonl": path.as_posix(),
        "rows_scanned": rows_scanned,
        "rows_with_snippet_candidates": rows_with_candidates,
        "snippet_candidates_total": snippet_candidates_total,
        "wire_match_count": wire_match_count,
        "wire_miss_count": wire_miss_count,
        "wire_match_rate": round(wire_match_count / denom, 6) if denom else 1.0,
        "non_canonical_mask_skipped": non_canonical_skipped,
        "misses_sample": misses,
    }


def run_coverage_eval(
    inputs: list[Path],
    *,
    shard_path: Path,
    catalog_path: Path,
    min_score: int = 1,
) -> dict[str, Any]:
    shard = load_shard(shard_path)
    catalog_rows = load_template_catalog(catalog_path)
    per_corpus: list[dict[str, Any]] = []
    for path in inputs:
        if not path.is_file():
            per_corpus.append(
                {
                    "input_jsonl": path.as_posix(),
                    "missing": True,
                    "wire_match_rate": 0.0,
                }
            )
            continue
        per_corpus.append(
            evaluate_corpus_snippet_coverage(
                path,
                shard=shard,
                catalog_rows=catalog_rows,
                min_score=min_score,
            )
        )

    total_candidates = sum(int(c.get("snippet_candidates_total") or 0) for c in per_corpus)
    total_match = sum(int(c.get("wire_match_count") or 0) for c in per_corpus)
    missing_inputs = [c["input_jsonl"] for c in per_corpus if c.get("missing")]
    aggregate_match_rate = round(total_match / total_candidates, 6) if total_candidates else 1.0

    return {
        "schema": "zone_ko_premium_cs_template_catalog_coverage_v1",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "research_only": True,
        "shard_json": shard_path.as_posix(),
        "catalog_jsonl": catalog_path.as_posix(),
        "catalog_row_count": len(catalog_rows),
        "input_count": len(inputs),
        "missing_inputs": missing_inputs,
        "min_score": min_score,
        "canonical_mask_token": "███",
        "corpora": per_corpus,
        "aggregate": {
            "corpus_count": len(inputs),
            "snippet_candidates_total": total_candidates,
            "wire_match_count": total_match,
            "wire_match_rate": aggregate_match_rate,
            "all_corpora_present": len(missing_inputs) == 0,
            "full_wire_match": total_candidates > 0 and total_match == total_candidates,
        },
    }


def write_coverage_report(report: dict[str, Any], *, report_path: Path, artifact_path: Path) -> None:
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(payload, encoding="utf-8")
