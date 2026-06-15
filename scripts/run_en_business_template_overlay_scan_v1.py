#!/usr/bin/env python3
"""[HYPO] Run en business template overlay + tenant must_keep twin scan (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.en_business_template_overlay_scan_v1_lib import (  # noqa: E402
    run_overlay_scan,
    write_overlay_report,
)

DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_h_en_business_batch_extract_manifest_v1.json"
DEFAULT_SHARD = ROOT / "codebook/shards/zone_h_en_business_v1.json"
DEFAULT_CATALOG = ROOT / "codebook/templates/zone_h_en_business_templates_v1.jsonl"
DEFAULT_TEMPLATE_MANIFEST = ROOT / "codebook/templates/zone_h_en_business_templates_manifest_v1.json"
DEFAULT_REPORT = ROOT / "reports/en_business_template_overlay_scan_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/en_business_template_overlay_scan_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="[HYPO] en business template overlay twin scan")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--template-manifest", type=Path, default=DEFAULT_TEMPLATE_MANIFEST)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--saving-rate-floor", type=float, default=0.0)
    args = ap.parse_args()

    if args.manifest.is_file():
        batch = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = batch.get("input_jsonl") or batch.get("inputs") or []
        inputs = [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = []

    report = run_overlay_scan(
        inputs,
        shard_path=args.shard_json,
        catalog_path=args.catalog,
        manifest_path=args.template_manifest,
        min_score=args.min_score,
        saving_rate_floor=args.saving_rate_floor,
    )
    write_overlay_report(report, report_path=args.report_out, artifact_path=args.artifact_out)
    agg = report["aggregate"]
    print(
        json.dumps(
            {
                "ok": True,
                "wire_match_rate": agg["wire_match_rate"],
                "exact_restore_rate_on_matched": agg["exact_restore_rate_on_matched"],
                "tenant_overlay_rate_on_matched": agg["tenant_overlay_rate_on_matched"],
                "min_saving_rate_observed": agg["min_saving_rate_observed"],
                "full_wire_and_twin_pass": agg["full_wire_and_twin_pass"],
                "report_out": str(args.report_out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg["full_wire_and_twin_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
