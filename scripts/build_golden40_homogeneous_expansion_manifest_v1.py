#!/usr/bin/env python3
"""Build Golden 40 homogeneous expansion manifest (B-track, read-only SSOT catalog)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
IEOMA_SASANG = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_sasang_v1.json"
LOGOS_SUBSET = ROOT / "docs/final/artifacts/MULTILENS_LOGOS_GRAPH_SUBSET_V1.json"
LOGOS_VERSE_LANE = ROOT / "docs/final/artifacts/golden_40_logos_verse_compression_lane_v1.json"
EN_OPS_LANE = ROOT / "docs/final/artifacts/golden_40_en_ops_compression_lane_v1.json"
REGISTRY = ROOT / "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/golden_40_homogeneous_expansion_manifest_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _case_count(path: Path) -> int:
    if not path.is_file():
        return 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    return len(doc.get("compression_cases") or [])


def _golden_ids() -> list[str]:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    return [str(c.get("id")) for c in doc.get("compression_cases") or [] if c.get("id")]


def _logos_extra_count() -> int:
    if not LOGOS_SUBSET.is_file():
        return 0
    doc = json.loads(LOGOS_SUBSET.read_text(encoding="utf-8"))
    golden_ids = set(_golden_ids())
    extra = 0
    for row in doc.get("compression_cases") or []:
        cid = str(row.get("id") or "")
        if cid and cid not in golden_ids:
            extra += 1
    return extra


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden 40 homogeneous expansion manifest builder.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    golden_n = _case_count(INPUT_V2)
    ieoma_n = _case_count(IEOMA_SASANG)
    logos_verse_n = _case_count(LOGOS_VERSE_LANE)
    en_ops_n = _case_count(EN_OPS_LANE)
    logos_extra = _logos_extra_count()
    full_max = golden_n + logos_verse_n + ieoma_n

    pools: list[dict[str, Any]] = [
        {
            "pool_mode": "golden_core_only",
            "label": "Frozen Golden 40 (Track A bench)",
            "golden_core_cases": golden_n,
            "expansion_cases_max": 0,
            "max_eval_case_count": golden_n,
            "dryrun_flag": "--pool-mode golden_core_only",
            "headline_claim_allowed": False,
            "note": "No expansion beyond 40; use for baseline replay only.",
        },
        {
            "pool_mode": "homogeneous_sasang_ko",
            "label": "Golden 40 + ijeoma_sasang KO corpus [HYPO boundary]",
            "golden_core_cases": golden_n,
            "expansion_cases_max": ieoma_n,
            "max_eval_case_count": golden_n + ieoma_n,
            "expansion_input_path": str(IEOMA_SASANG.relative_to(ROOT)).replace("\\", "/"),
            "dryrun_flag": "--pool-mode homogeneous_sasang_ko",
            "headline_claim_allowed": False,
            "boundary_ack": "ijeoma_sasang is B-track [HYPO] — lab confidence only, not MS 47.5% merge",
            "recommended_targets": [40, 80, 120, min(200, golden_n + ieoma_n)],
        },
        {
            "pool_mode": "homogeneous_logos_verse",
            "label": "Golden 40 + logos verse_decoded_v2 stride sample [HYPO]",
            "golden_core_cases": golden_n,
            "expansion_cases_max": logos_verse_n,
            "max_eval_case_count": golden_n + logos_verse_n,
            "expansion_input_path": str(LOGOS_VERSE_LANE.relative_to(ROOT)).replace("\\", "/"),
            "harvest_script": "scripts/build_golden40_logos_verse_compression_lane_v1.py",
            "dryrun_flag": "--pool-mode homogeneous_logos_verse",
            "headline_claim_allowed": False,
            "recommended_targets": [40, 80, 120, 200, min(400, golden_n + logos_verse_n)],
        },
        {
            "pool_mode": "homogeneous_full",
            "label": "Golden 40 + logos verse + ijeoma_sasang (no finance/enterprise)",
            "golden_core_cases": golden_n,
            "expansion_cases_max": logos_verse_n + ieoma_n,
            "max_eval_case_count": full_max,
            "dryrun_flag": "--pool-mode homogeneous_full",
            "headline_claim_allowed": False,
            "recommended_targets": [40, 80, 120, 200, min(400, full_max)],
        },
        {
            "pool_mode": "homogeneous_en_ops",
            "label": "Golden 40 + EN ops/governance MD proxy (cmp2_001–010 band)",
            "golden_core_cases": golden_n,
            "expansion_cases_max": en_ops_n,
            "max_eval_case_count": golden_n + en_ops_n,
            "expansion_input_path": str(EN_OPS_LANE.relative_to(ROOT)).replace("\\", "/"),
            "dryrun_flag": "--pool-mode homogeneous_en_ops",
            "headline_claim_allowed": False,
            "note": "Build lane via build_universal_compression_bench_lane_from_md_v1 + golden_40_en_ops_lane_manifest_v1.json",
        },
        {
            "pool_mode": "mixed_matrix",
            "label": "Golden 40 + Universal Matrix lanes (heterogeneous)",
            "golden_core_cases": golden_n,
            "expansion_cases_max": None,
            "max_eval_case_count": None,
            "registry_path": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
            "dryrun_flag": "--pool-mode mixed_matrix",
            "headline_claim_allowed": False,
            "warning": "Blended Jaccard may dilute vs golden_core — see golden_40_expansion_dryrun mixed_domain_dilution_observed",
        },
    ]

    doc: dict[str, Any] = {
        "schema": "golden_40_homogeneous_expansion_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": "B-track catalog — does not replace MULTILENS_PERFORMANCE_EVAL_INPUT_V2 or ACTIVE report",
        "golden_frozen_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "golden_case_ids_sample": _golden_ids()[:5],
        "logos_graph_subset": {
            "path": str(LOGOS_SUBSET.relative_to(ROOT)).replace("\\", "/"),
            "compression_cases": _case_count(LOGOS_SUBSET),
            "net_new_vs_golden": logos_extra,
            "note": "Logos subset cases are mostly cmp2_* already in Golden 40 — not a size expansion source.",
        },
        "pools": pools,
        "news_readiness": False,
        "promotion_recommendation": "HOLD",
    }

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        f"homogeneous_sasang_ko max={golden_n + ieoma_n} "
        f"logos_verse max={golden_n + logos_verse_n} full max={full_max}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
