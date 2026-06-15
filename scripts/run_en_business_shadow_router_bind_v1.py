#!/usr/bin/env python3
"""[HYPO] Run en business shadow router bind eval (corpus_tag → zone_h_en_business_v1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.en_business_shadow_router_bind_v1_lib import (  # noqa: E402
    DEFAULT_BIND_SPEC,
    run_shadow_bind_eval,
    write_shadow_bind_report,
)

DEFAULT_MANIFEST = ROOT / "data/compression/fixtures/zone_h_en_business_batch_extract_manifest_v1.json"
DEFAULT_REPORT = ROOT / "reports/en_business_shadow_router_bind_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/en_business_shadow_router_bind_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="[HYPO] en business shadow router bind eval")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--bind-spec", type=Path, default=DEFAULT_BIND_SPEC)
    ap.add_argument("--shards-root", type=Path, default=ROOT / "codebook/shards")
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--artifact-out", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    if args.manifest.is_file():
        batch = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        rel_paths = batch.get("input_jsonl") or batch.get("inputs") or []
        inputs = [(ROOT / p) if not Path(p).is_absolute() else Path(p) for p in rel_paths]
    else:
        inputs = []

    report = run_shadow_bind_eval(
        inputs,
        spec_path=args.bind_spec,
        shards_root=args.shards_root,
    )
    write_shadow_bind_report(report, report_path=args.report_out, artifact_path=args.artifact_out)
    agg = report["aggregate"]
    print(
        json.dumps(
            {
                "ok": True,
                "shadow_applied_count": agg["shadow_applied_count"],
                "divergence_count": agg["divergence_count"],
                "divergence_rate": agg["divergence_rate"],
                "full_shadow_bind_pass": agg["full_shadow_bind_pass"],
                "report_out": str(args.report_out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg["full_shadow_bind_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
