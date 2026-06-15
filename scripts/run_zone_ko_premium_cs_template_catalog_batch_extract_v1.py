#!/usr/bin/env python3
"""Batch extract zone_ko_premium_cs template seeds from multiple JSONL corpora."""

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

from scripts.compression_ko_premium_cs_deep_pack_v1_lib import load_template_catalog  # noqa: E402
from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import (  # noqa: E402
    assign_prospect_template_ids,
    dedupe_seeds,
    extract_from_jsonl,
    load_shard,
    normalize_snippet,
)
from scripts.merge_zone_ko_premium_cs_template_prospect_v1_lib import (  # noqa: E402
    max_prospect_index,
)

DEFAULT_SHARD = ROOT / "codebook/shards/zone_ko_premium_cs_v1.json"
DEFAULT_CATALOG = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_ko_premium_cs_templates_prospect_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_ko_premium_cs_batch_extract_manifest_v1.json"
DEFAULT_BATCH_REPORT = ROOT / "reports/zone_ko_premium_cs_template_catalog_batch_extract_v1_latest.json"
DEFAULT_BATCH_ARTIFACT = ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_batch_extract_v1_latest.json"

DEFAULT_INPUTS = [
    "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1_bodyonly_v1.jsonl",
    "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1_remainder_000_017_v1.jsonl",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _existing_snippets(*paths: Path) -> set[str]:
    out: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        for row in load_template_catalog(path):
            out.add(normalize_snippet(str(row.get("snippet") or "")))
    return out


def run_batch_extract(
    inputs: list[Path],
    *,
    shard_path: Path,
    catalog_path: Path,
    prospect_path: Path,
    min_score: int,
    max_rows: int,
) -> dict[str, Any]:
    shard = load_shard(shard_path)
    existing = _existing_snippets(catalog_path, prospect_path)
    per_corpus: list[dict[str, Any]] = []
    aggregate_seeds: list[dict[str, Any]] = []
    for inp in inputs:
        if not inp.is_file():
            per_corpus.append({"input_jsonl": _rel(inp), "ok": False, "error": "missing"})
            continue
        result = extract_from_jsonl(
            inp,
            shard=shard,
            existing_snippets=existing,
            min_score=min_score,
            max_rows=max_rows,
        )
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
                    "extract_score": seed.get("extract_score"),
                }
            )
            existing.add(normalize_snippet(str(seed["snippet"])))
    deduped = dedupe_seeds(aggregate_seeds)
    existing_prospect = load_template_catalog(prospect_path) if prospect_path.is_file() else []
    start_index = max_prospect_index(existing_prospect) + 1 if existing_prospect else 1
    prospect_rows = assign_prospect_template_ids(deduped, start_index=start_index)
    return {
        "schema": "zone_ko_premium_cs_template_catalog_batch_extract_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "merge_policy": "prospect_only_no_auto_merge",
        "input_count": len(inputs),
        "per_corpus": per_corpus,
        "aggregate_stats": {
            "candidates_raw": len(aggregate_seeds),
            "candidates_deduped": len(deduped),
            "prospect_count": len(prospect_rows),
            "prospect_id_start_index": start_index,
        },
        "prospect_rows": prospect_rows,
        "prospect_template_ids": [r["template_id"] for r in prospect_rows],
        "reproduce": "py scripts/run_zone_ko_premium_cs_template_catalog_batch_extract_v1.py --append-prospect",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch extract ko premium cs template seeds")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--prospect-out", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_BATCH_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_BATCH_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=1)
    ap.add_argument("--max-rows", type=int, default=50)
    ap.add_argument("--write-prospect", action="store_true", help="Replace prospect catalog with batch rows only")
    ap.add_argument("--append-prospect", action="store_true", help="Append batch rows to existing prospect catalog")
    args = ap.parse_args()
    if args.manifest.is_file():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = manifest.get("input_jsonl") or manifest.get("inputs") or []
        inputs = [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = [ROOT / p for p in DEFAULT_INPUTS]
    report = run_batch_extract(
        inputs,
        shard_path=args.shard_json,
        catalog_path=args.catalog,
        prospect_path=args.prospect_out,
        min_score=args.min_score,
        max_rows=args.max_rows,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    new_rows = report.get("prospect_rows") or []
    if args.write_prospect or args.append_prospect:
        lines = []
        if args.append_prospect and args.prospect_out.is_file():
            for line in args.prospect_out.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    lines.append(line.strip())
        lines.extend(json.dumps(row, ensure_ascii=False) for row in new_rows)
        args.prospect_out.parent.mkdir(parents=True, exist_ok=True)
        args.prospect_out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "input_count": report["input_count"],
                "prospect_count": report["aggregate_stats"]["prospect_count"],
                "report_out": str(args.report_out),
                "prospect_written": bool(args.write_prospect or args.append_prospect),
                "append_mode": bool(args.append_prospect),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
