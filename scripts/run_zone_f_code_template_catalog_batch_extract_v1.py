#!/usr/bin/env python3
"""Batch extract zone_f_code template seeds from multiple customer JSONL corpora.

Aggregates deduped prospect rows across inputs. research_only · no production merge.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_coding_deep_pack_v1_lib import load_template_catalog  # noqa: E402
from scripts.extract_zone_f_code_template_seeds_v1_lib import (  # noqa: E402
    assign_prospect_template_ids,
    dedupe_seeds,
    extract_from_jsonl,
    load_zone_f_code_shard,
)

DEFAULT_SHARD = ROOT / "codebook/shards/zone_f_code.json"
DEFAULT_CATALOG = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_f_code_templates_prospect_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_f_code_batch_extract_manifest_v1.json"
DEFAULT_BATCH_REPORT = ROOT / "reports/zone_f_code_template_catalog_batch_extract_v1_latest.json"
DEFAULT_BATCH_ARTIFACT = ROOT / "docs/final/artifacts/zone_f_code_template_catalog_batch_extract_v1_latest.json"

DEFAULT_INPUTS = [
    "data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl",
    "data/compression/stateless_poc_prospect_tactical-b-free-audit-v1_v1.jsonl",
    "data/compression/stateless_poc_prospect_customer-pilot-smoke-v1_v1.jsonl",
    "data/compression/examples/customer_masked_pilot_smoke_v1.jsonl",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _existing_snippets(catalog_path: Path) -> set[str]:
    if not catalog_path.is_file():
        return set()
    return {str(r.get("snippet") or "") for r in load_template_catalog(catalog_path)}


def run_batch_extract(
    inputs: list[Path],
    *,
    shard_path: Path,
    catalog_path: Path,
    min_score: int,
) -> dict[str, Any]:
    shard = load_zone_f_code_shard(shard_path)
    existing = _existing_snippets(catalog_path)
    per_corpus: list[dict[str, Any]] = []
    aggregate_seeds: list[dict[str, Any]] = []
    for inp in inputs:
        if not inp.is_file():
            per_corpus.append({"input_jsonl": _rel(inp), "ok": False, "error": "missing"})
            continue
        result = extract_from_jsonl(inp, shard=shard, existing_snippets=existing, min_score=min_score)
        per_corpus.append(
            {
                "input_jsonl": _rel(inp),
                "ok": True,
                "rows_scanned": result["rows_scanned"],
                "candidates_novel": result["candidates_novel"],
                "prospect_template_ids": [r["template_id"] for r in result["prospect_rows"]],
            }
        )
        for seed in result["prospect_rows"]:
            aggregate_seeds.append(
                {
                    "snippet": seed["snippet"],
                    "snippet_sha256": seed.get("snippet_sha256"),
                    "language": seed.get("language"),
                    "must_keep_terms": seed.get("must_keep_terms"),
                    "source_row_id": seed.get("source_row_id"),
                    "source_jsonl": _rel(inp),
                }
            )
            existing.add(str(seed["snippet"]))
    deduped = dedupe_seeds(aggregate_seeds)
    prospect_rows = assign_prospect_template_ids(deduped)
    return {
        "schema": "zone_f_code_template_catalog_batch_extract_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "merge_policy": "prospect_only_no_auto_merge",
        "input_count": len(inputs),
        "per_corpus": per_corpus,
        "aggregate_stats": {
            "candidates_raw": len(aggregate_seeds),
            "candidates_deduped": len(deduped),
            "prospect_count": len(prospect_rows),
        },
        "prospect_rows": prospect_rows,
        "prospect_template_ids": [r["template_id"] for r in prospect_rows],
        "reproduce": "py scripts/run_zone_f_code_template_catalog_batch_extract_v1.py --write-prospect",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch extract zone_f_code template seeds")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="JSON list of input_jsonl paths")
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--prospect-out", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_BATCH_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_BATCH_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--write-prospect", action="store_true")
    args = ap.parse_args()
    if args.manifest.is_file():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = manifest.get("input_jsonl") or manifest.get("inputs") or []
        inputs = [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = [ROOT / p for p in DEFAULT_INPUTS]
    report = run_batch_extract(inputs, shard_path=args.shard_json, catalog_path=args.catalog, min_score=args.min_score)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    if args.write_prospect:
        rows = report.get("prospect_rows") or []
        lines = [json.dumps(row, ensure_ascii=False) for row in rows]
        args.prospect_out.parent.mkdir(parents=True, exist_ok=True)
        args.prospect_out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "input_count": report["input_count"],
                "prospect_count": report["aggregate_stats"]["prospect_count"],
                "report_out": str(args.report_out),
                "prospect_written": bool(args.write_prospect),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
