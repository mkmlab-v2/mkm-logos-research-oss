#!/usr/bin/env python3
"""Run zone_hardware_machine prospect catalog wire-match coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.zone_hardware_machine_template_catalog_coverage_v1_lib import build_coverage_report  # noqa: E402

DEFAULT_CATALOG = ROOT / "codebook/templates/zone_hardware_machine_templates_prospect_v1.jsonl"
DEFAULT_SHARD = ROOT / "codebook/shards/zone_hardware_machine.json"
DEFAULT_INPUT = ROOT / "data/btrack_fixtures/zone_hardware_machine_log_samples_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/zone_hardware_machine_template_catalog_coverage_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_hardware_machine_template_catalog_coverage_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--input-jsonl", type=Path, action="append", default=[])
    args = ap.parse_args()

    inputs = [p if p.is_absolute() else ROOT / p for p in args.input_jsonl] if args.input_jsonl else [DEFAULT_INPUT]
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
