#!/usr/bin/env python3
"""Run zone_ko_premium_cs template catalog wire coverage eval (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.zone_ko_premium_cs_template_catalog_coverage_v1_lib import (  # noqa: E402
    run_coverage_eval,
    write_coverage_report,
)

DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_ko_premium_cs_batch_extract_manifest_v1.json"
DEFAULT_SHARD = ROOT / "codebook/shards/zone_ko_premium_cs_v1.json"
DEFAULT_CATALOG = ROOT / "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/zone_ko_premium_cs_template_catalog_coverage_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_ko_premium_cs_template_catalog_coverage_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="zone_ko_premium_cs template catalog coverage")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=1)
    args = ap.parse_args()

    if args.manifest.is_file():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = manifest.get("input_jsonl") or manifest.get("inputs") or []
        inputs = [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = []

    report = run_coverage_eval(
        inputs,
        shard_path=args.shard_json,
        catalog_path=args.catalog,
        min_score=args.min_score,
    )
    write_coverage_report(report, report_path=args.report_out, artifact_path=args.artifact_out)
    print(
        json.dumps(
            {
                "ok": True,
                "wire_match_rate": report["aggregate"]["wire_match_rate"],
                "full_wire_match": report["aggregate"]["full_wire_match"],
                "report_out": str(args.report_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
