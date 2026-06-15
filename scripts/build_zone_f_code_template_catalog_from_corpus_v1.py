#!/usr/bin/env python3
"""Build zone_f_code prospect template catalog from customer JSONL corpora.

Extracts code snippets (fenced blocks or code-like rows), scores against zone_f_code shard,
writes prospect JSONL + extract report. Does NOT auto-merge into production catalog.

research_only · SEND_GATE HOLD · no ACTIVE mutation.
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

from scripts.compression_coding_deep_pack_v1_lib import (  # noqa: E402
    load_template_catalog,
    measure_template_wire_twin,
)
from scripts.extract_zone_f_code_template_seeds_v1_lib import (  # noqa: E402
    extract_from_jsonl,
    load_zone_f_code_shard,
)

DEFAULT_SHARD = ROOT / "codebook/shards/zone_f_code.json"
DEFAULT_CATALOG = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_f_code_templates_prospect_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/zone_f_code_template_catalog_extract_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_f_code_template_catalog_extract_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _existing_snippets(catalog_path: Path) -> set[str]:
    if not catalog_path.is_file():
        return set()
    return {str(r.get("snippet") or "") for r in load_template_catalog(catalog_path)}


def _evaluate_prospect_twins(
    prospect_rows: list[dict[str, Any]],
    catalog_sha256: str,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for row in prospect_rows:
        twin = measure_template_wire_twin(
            original_snippet=str(row["snippet"]),
            template_id=str(row["template_id"]),
            catalog_sha256=catalog_sha256,
            catalog_rows=prospect_rows,
        )
        cases.append({**twin, "prospect": True})
    return cases


def build_extract_report(
    *,
    input_jsonl: Path,
    shard_path: Path,
    catalog_path: Path,
    min_score: int,
) -> dict[str, Any]:
    shard = load_zone_f_code_shard(shard_path)
    existing = _existing_snippets(catalog_path)
    result = extract_from_jsonl(
        input_jsonl,
        shard=shard,
        existing_snippets=existing,
        min_score=min_score,
    )
    prospect_rows = result["prospect_rows"]
    twin_cases: list[dict[str, Any]] = []
    if prospect_rows:
        from scripts.build_compression_coding_deep_pack_gate_v1 import _sha256_file  # noqa: WPS433
        import tempfile

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as tmp:
            for row in prospect_rows:
                tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
            tmp_path = Path(tmp.name)
        catalog_hash = _sha256_file(tmp_path)
        twin_cases = _evaluate_prospect_twins(prospect_rows, catalog_hash)
        tmp_path.unlink(missing_ok=True)
    ok_twins = [c for c in twin_cases if c.get("exact_restore_ok")]
    return {
        "schema": "zone_f_code_template_catalog_extract_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "input_jsonl": input_jsonl.relative_to(ROOT).as_posix()
        if input_jsonl.is_relative_to(ROOT)
        else input_jsonl.as_posix(),
        "production_catalog": catalog_path.relative_to(ROOT).as_posix()
        if catalog_path.is_relative_to(ROOT)
        else catalog_path.as_posix(),
        "production_catalog_row_count": len(existing),
        "prospect_catalog_default": DEFAULT_PROSPECT.relative_to(ROOT).as_posix(),
        "merge_policy": "prospect_only_no_auto_merge",
        "extract_stats": {
            "rows_scanned": result["rows_scanned"],
            "candidates_raw": result["candidates_raw"],
            "candidates_deduped": result["candidates_deduped"],
            "candidates_novel": result["candidates_novel"],
            "candidates_skipped_existing": result["candidates_skipped_existing"],
        },
        "prospect_template_ids": [r["template_id"] for r in prospect_rows],
        "prospect_rows": prospect_rows,
        "twin_preview": {
            "case_count": len(twin_cases),
            "exact_restore_pass_count": len(ok_twins),
            "mean_saving_rate": round(
                sum(float(c.get("saving_rate") or 0.0) for c in ok_twins) / max(1, len(ok_twins)),
                6,
            )
            if ok_twins
            else 0.0,
        },
        "twin_cases": twin_cases,
        "reproduce": f"py scripts/build_zone_f_code_template_catalog_from_corpus_v1.py --input-jsonl {input_jsonl.relative_to(ROOT).as_posix() if input_jsonl.is_relative_to(ROOT) else input_jsonl.as_posix()} --write-prospect",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract zone_f_code template seeds from customer JSONL")
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--prospect-out", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument(
        "--write-prospect",
        action="store_true",
        help="Write prospect catalog JSONL (default: report only)",
    )
    args = ap.parse_args()
    if not args.input_jsonl.is_file():
        print(f"MISSING input: {args.input_jsonl}", file=sys.stderr)
        return 1
    report = build_extract_report(
        input_jsonl=args.input_jsonl,
        shard_path=args.shard_json,
        catalog_path=args.catalog,
        min_score=args.min_score,
    )
    prospect_rows = report.get("prospect_rows") or []
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    if args.write_prospect:
        lines = [json.dumps(row, ensure_ascii=False) for row in prospect_rows]
        args.prospect_out.parent.mkdir(parents=True, exist_ok=True)
        args.prospect_out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "rows_scanned": report["extract_stats"]["rows_scanned"],
                "prospect_count": len(prospect_rows),
                "exact_restore_preview": report["twin_preview"]["exact_restore_pass_count"],
                "report_out": str(args.report_out),
                "prospect_written": bool(args.write_prospect),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
