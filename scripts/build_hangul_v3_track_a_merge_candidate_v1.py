#!/usr/bin/env python3
"""Build Track A merge preflight candidate — 41708 base + v2 overlay (+ v3 evidence metadata)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hangul_v3_track_a_merge_lib_v1 import (  # noqa: E402
    build_production_preserve_v3_metadata_refresh,
    build_production_union_v2_on_base,
)

CONTRACT = ROOT / "docs/final/artifacts/HANGUL_V3_TRACK_A_MERGE_PREFLIGHT_CONTRACT_V1.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_PROD = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
DEFAULT_V3 = PILOT / "master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json"
DEFAULT_V2_MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json"
DEFAULT_V3_MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v3_golden40_evidence.json"
DEFAULT_REPORT = ROOT / "reports/hangul_v3_track_a_merge_candidate_build_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile",
        choices=("production_union_v2_full_on_base", "production_preserve_v3_metadata_refresh"),
        default="production_union_v2_full_on_base",
    )
    ap.add_argument("--production", type=Path, default=DEFAULT_PROD)
    ap.add_argument("--v3-candidate", type=Path, default=DEFAULT_V3)
    ap.add_argument("--v2-manifest", type=Path, default=DEFAULT_V2_MANIFEST)
    ap.add_argument("--v3-manifest", type=Path, default=DEFAULT_V3_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--skip-v3-metadata", action="store_true")
    args = ap.parse_args()

    prod = args.production if args.production.is_absolute() else (ROOT / args.production)
    v3 = args.v3_candidate if args.v3_candidate.is_absolute() else (ROOT / args.v3_candidate)
    missing = [p for p in (prod, v3) if not p.is_file()]
    if missing:
        print("ABORT: missing", [str(p) for p in missing])
        return 1

    import json as _json

    v3_doc = _json.loads(v3.read_text(encoding="utf-8"))
    prod_doc = _json.loads(prod.read_text(encoding="utf-8"))

    if args.profile == "production_union_v2_full_on_base":
        v2_manifest = args.v2_manifest if args.v2_manifest.is_absolute() else (ROOT / args.v2_manifest)
        v3_manifest = args.v3_manifest if args.v3_manifest.is_absolute() else (ROOT / args.v3_manifest)
        if not v2_manifest.is_file():
            print("ABORT: v2 manifest missing")
            return 1
        _, build_report = build_production_union_v2_on_base(
            production_path=prod,
            manifest_path=v2_manifest,
            v3_manifest_path=None if args.skip_v3_metadata else v3_manifest,
            enrich_v3=not args.skip_v3_metadata,
        )
    else:
        v3_manifest = args.v3_manifest if args.v3_manifest.is_absolute() else (ROOT / args.v3_manifest)
        if not v3_manifest.is_file():
            print("ABORT: v3 manifest missing")
            return 1
        _, build_report = build_production_preserve_v3_metadata_refresh(
            production_path=prod,
            v3_manifest_path=v3_manifest,
        )

    from scripts.hangul_v3_track_a_merge_lib_v1 import subset_audit  # noqa: E402

    build_report["schema"] = "hangul_v3_track_a_merge_candidate_build_v1"
    build_report["v3_subset_audit_vs_production"] = subset_audit(prod_doc, v3_doc)
    build_report["contract"] = str(CONTRACT.relative_to(ROOT)).replace("\\", "/") if CONTRACT.is_file() else None
    build_report["reproduce"] = (
        f"py scripts/build_hangul_v3_track_a_merge_candidate_v1.py --profile {args.profile}"
    )

    report_path = args.report if args.report.is_absolute() else (ROOT / args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(build_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(report_path.relative_to(ROOT)).replace("\\", "/"),
                "profile": args.profile,
                "candidate_ko": build_report.get("candidate_ko"),
                "production_ko": build_report.get("production_ko"),
                "v3_is_subset": (build_report.get("v3_subset_audit_vs_production") or {}).get(
                    "v3_is_subset_of_production"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
