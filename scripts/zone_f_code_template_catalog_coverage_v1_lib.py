"""Measure zone_f_code template catalog wire-match coverage on customer JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.compression_coding_deep_pack_v1_lib import (
    load_template_catalog,
    resolve_template_match,
)
from scripts.extract_zone_f_code_template_seeds_v1_lib import (
    extract_candidates_from_text,
    iter_jsonl_rows,
    load_zone_f_code_shard,
    row_text_blobs,
    shard_keywords,
)


def evaluate_corpus_coverage(
    input_jsonl: Path,
    *,
    catalog_path: Path,
    shard_path: Path,
    min_score: int = 2,
) -> dict[str, Any]:
    shard = load_zone_f_code_shard(shard_path)
    keywords = shard_keywords(shard)
    catalog_rows = load_template_catalog(catalog_path) if catalog_path.is_file() else []
    rows_scanned = 0
    rows_with_candidates = 0
    snippet_candidates = 0
    exact_matches = 0
    literal_slot_matches = 0
    no_match = 0
    per_row: list[dict[str, Any]] = []

    for obj in iter_jsonl_rows(input_jsonl):
        rows_scanned += 1
        row_id = str(obj.get("id") or obj.get("case_id") or rows_scanned)
        row_candidates: list[dict[str, Any]] = []
        for blob in row_text_blobs(obj):
            for snippet in extract_candidates_from_text(blob, keywords=keywords, min_score=min_score):
                snippet_candidates += 1
                resolved = resolve_template_match(snippet, catalog_rows)
                if resolved is None:
                    no_match += 1
                    match_kind = "no_match"
                else:
                    _tid, slots = resolved
                    if slots:
                        literal_slot_matches += 1
                        match_kind = "literal_slot"
                    else:
                        exact_matches += 1
                        match_kind = "exact"
                row_candidates.append(
                    {
                        "snippet_preview": snippet[:120],
                        "match_kind": match_kind,
                        "template_id": resolved[0] if resolved else None,
                    }
                )
        if row_candidates:
            rows_with_candidates += 1
            per_row.append({"row_id": row_id, "candidates": row_candidates})

    wire_match_count = exact_matches + literal_slot_matches
    return {
        "input_jsonl": input_jsonl.as_posix(),
        "rows_scanned": rows_scanned,
        "rows_with_code_candidates": rows_with_candidates,
        "snippet_candidates_total": snippet_candidates,
        "wire_match_count": wire_match_count,
        "wire_match_rate": round(wire_match_count / snippet_candidates, 6) if snippet_candidates else 0.0,
        "exact_match_count": exact_matches,
        "literal_slot_match_count": literal_slot_matches,
        "fallback_count": no_match,
        "catalog_row_count": len(catalog_rows),
        "per_row": per_row,
    }


def build_coverage_report(
    corpora: list[Path],
    *,
    catalog_path: Path,
    shard_path: Path,
    min_score: int = 2,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    corpus_results: list[dict[str, Any]] = []
    total_candidates = 0
    total_wire = 0
    for path in corpora:
        if not path.is_file():
            corpus_results.append({"input_jsonl": path.as_posix(), "ok": False, "error": "missing"})
            continue
        row = evaluate_corpus_coverage(
            path,
            catalog_path=catalog_path,
            shard_path=shard_path,
            min_score=min_score,
        )
        row["ok"] = True
        corpus_results.append(row)
        total_candidates += int(row["snippet_candidates_total"])
        total_wire += int(row["wire_match_count"])
    return {
        "schema": "zone_f_code_template_catalog_coverage_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "catalog_path": catalog_path.as_posix(),
        "aggregate": {
            "corpus_count": len(corpora),
            "snippet_candidates_total": total_candidates,
            "wire_match_count": total_wire,
            "wire_match_rate": round(total_wire / total_candidates, 6) if total_candidates else 0.0,
            "note": "Wire match = exact or literal_slot against production catalog; not customer SLA.",
        },
        "corpora": corpus_results,
        "reproduce": "py scripts/run_zone_f_code_template_catalog_coverage_v1.py",
    }
