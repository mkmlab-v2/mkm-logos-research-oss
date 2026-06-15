#!/usr/bin/env python3
"""Run zone_f_code template catalog wire-match coverage on customer JSONL corpora.

research_only · SEND_GATE HOLD · separate from Golden-40 / Tier A metrics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.zone_f_code_template_catalog_coverage_v1_lib import build_coverage_report  # noqa: E402

DEFAULT_CATALOG = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"
DEFAULT_SHARD = ROOT / "codebook/shards/zone_f_code.json"
DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_f_code_batch_extract_manifest_v1.json"
DEFAULT_REPORT = ROOT / "reports/zone_f_code_template_catalog_coverage_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_f_code_template_catalog_coverage_v1_latest.json"

DEFAULT_INPUTS = [
    "data/compression/fixtures/zone_f_code_corpus_extract_fixture_v1.jsonl",
    "data/compression/contributions/open_bench_coding_snippet_seed_v1.jsonl",
    "data/compression/stateless_poc_prospect_tactical-b-free-audit-v1_v1.jsonl",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Catalog wire-match coverage on JSONL corpora")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--input-jsonl", type=Path, action="append", default=[])
    args = ap.parse_args()
    if args.input_jsonl:
        inputs = [p if p.is_absolute() else ROOT / p for p in args.input_jsonl]
    elif args.manifest.is_file():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = manifest.get("input_jsonl") or manifest.get("inputs") or DEFAULT_INPUTS
        inputs = [ROOT / p if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = [ROOT / p for p in DEFAULT_INPUTS]
    report = build_coverage_report(
        inputs,
        catalog_path=args.catalog,
        shard_path=args.shard_json,
        min_score=args.min_score,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(payload, encoding="utf-8")
    args.artifact_out.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_out.write_text(payload, encoding="utf-8")
    agg = report["aggregate"]
    print(
        json.dumps(
            {
                "ok": True,
                "corpus_count": agg["corpus_count"],
                "snippet_candidates_total": agg["snippet_candidates_total"],
                "wire_match_rate": agg["wire_match_rate"],
                "report_out": str(args.report_out),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
