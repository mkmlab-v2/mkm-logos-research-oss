"""Measure zone_hardware_machine prospect catalog wire-match coverage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.build_zone_hardware_machine_prospect_v1 import _keywords, _load_shard, _row_text, _score_text
from scripts.compression_hardware_machine_deep_pack_v1_lib import (
    load_template_catalog,
    resolve_template_match,
)


def iter_jsonl_rows(path: Path):
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def evaluate_corpus_coverage(
    input_jsonl: Path,
    *,
    catalog_path: Path,
    shard_path: Path,
    min_score: int = 2,
) -> dict[str, Any]:
    shard = _load_shard(shard_path)
    keywords = _keywords(shard)
    catalog_rows = load_template_catalog(catalog_path) if catalog_path.is_file() else []
    rows_scanned = 0
    rows_with_candidates = 0
    snippet_candidates = 0
    wire_match_count = 0
    fallback_count = 0
    per_row: list[dict[str, Any]] = []

    for obj in iter_jsonl_rows(input_jsonl):
        rows_scanned += 1
        text = _row_text(obj)
        if not text:
            continue
        score = _score_text(text, keywords)
        if score < min_score:
            continue
        snippet_candidates += 1
        template_id = resolve_template_match(text, catalog_rows)
        if template_id:
            wire_match_count += 1
            match_kind = "exact"
        else:
            fallback_count += 1
            match_kind = "no_match"
        rows_with_candidates += 1
        per_row.append(
            {
                "row_id": str(obj.get("id") or rows_scanned),
                "snippet_preview": text[:120],
                "match_kind": match_kind,
                "template_id": template_id,
                "extract_score": score,
            }
        )

    return {
        "input_jsonl": input_jsonl.as_posix(),
        "rows_scanned": rows_scanned,
        "rows_with_candidates": rows_with_candidates,
        "snippet_candidates_total": snippet_candidates,
        "wire_match_count": wire_match_count,
        "wire_match_rate": round(wire_match_count / snippet_candidates, 6) if snippet_candidates else 0.0,
        "fallback_count": fallback_count,
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
        "schema": "zone_hardware_machine_template_catalog_coverage_v1",
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
            "note": "Prospect catalog only; merge to production forbidden without human sign-off.",
        },
        "corpora": corpus_results,
        "reproduce": "py scripts/run_zone_hardware_machine_template_catalog_coverage_v1.py",
    }
