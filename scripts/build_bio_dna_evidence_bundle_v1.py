#!/usr/bin/env python3
"""Build curated DNA promotion evidence bundle index + SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--bundle-id",
        default="evidence_bundle_20260524",
        help="Subdirectory under reports/",
    )
    ap.add_argument(
        "--cohort-rows",
        type=int,
        default=200,
        help="Documented real cohort row count for bundle metadata",
    )
    ns = ap.parse_args()

    bundle_dir = root / "reports" / ns.bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    curated: list[dict[str, str]] = [
        {"path": "reports/bio_dna_constitution_promotion_packet_v1_latest.json", "role": "promotion packet json"},
        {"path": "reports/bio_dna_constitution_promotion_packet_v1_latest.md", "role": "promotion packet markdown"},
        {"path": "reports/bio_dna_constitution_final_approval_latest.json", "role": "final approval + reaffirmation"},
        {"path": "reports/bio_dna_promotion_readiness_v1_latest.json", "role": "strict readiness 3/3"},
        {"path": "reports/bio_dna_promotion_threshold_sweep_v1_latest.json", "role": "threshold sweep"},
        {"path": "reports/bio_dna_ab_neutral_seed_stability_v1.json", "role": "neutral seed stability summary"},
        {"path": "reports/bio_dna_ab_neutral_seed_stability_v1.csv", "role": "neutral seed per-run table"},
        {
            "path": "reports/bio_dna_ab_holdout_eval_v1_autobuild_latest.json",
            "role": "neutral holdout eval (blind replay profiles)",
        },
        {"path": "reports/bio_dna_ab_autobuild_report_v1_latest.json", "role": "autobuild provenance"},
        {"path": "reports/bio_genotype_paper_snp_overlap_v1_latest.json", "role": "genotype-paper SNP overlap"},
        {"path": "reports/bio_paper_snp_mapping_coverage_autofill_v1.json", "role": "mapping coverage"},
    ]

    hash_entries: list[dict[str, Any]] = []
    missing: list[str] = []
    for item in curated:
        rel = item["path"].replace("/", "\\") if "\\" in str(root) else item["path"]
        p = root / rel.replace("\\", "/")
        if not p.is_file():
            missing.append(item["path"])
            continue
        hash_entries.append(
            {
                "path": item["path"],
                "sha256": _sha256(p),
                "bytes": p.stat().st_size,
            }
        )

    if missing:
        raise SystemExit(f"missing curated artifacts: {missing}")

    index: dict[str, Any] = {
        "schema": "bio_dna_evidence_bundle_index_v1",
        "bundle_id": ns.bundle_id,
        "generated_at_utc": _utc_now(),
        "purpose": "200-row real cohort DNA B-track research promotion snapshot (2026-05-24).",
        "scope_guardrails": {
            "research_only": True,
            "b_track_research_promotion_complete": True,
            "track_a_live_trading_auto_promotion_forbidden": True,
            "requires_human_review_for_live_promotion": True,
            "market_uplift_claim_scope": "research_ab_holdout_only",
        },
        "cohort_observations": {
            "real_lane_rows": ns.cohort_rows,
            "readiness_strict": "3/3",
            "seed_stability": "30/30",
        },
        "curated_artifacts": curated,
        "vault_only_inputs": [
            {
                "path": "tmp/bio_real_cohort_merged_with_sidecar_v1.csv",
                "role": "real cohort (not in git; mirrored to Vault)",
            },
            {
                "path": "tmp/bio_genotype_long_v1.csv",
                "role": "normalized genotype long (not in git; mirrored to Vault)",
            },
        ],
        "restore_pointer": "docs/final/artifacts/bio_dna_real_cohort_restore_pointer_v1.json",
        "exclusions_note": "Per-seed run dir reports/bio_dna_ab_neutral_seed_runs_v1/ excluded from curated hash set.",
    }

    manifest = {
        "schema": "bio_dna_evidence_hash_manifest_v1",
        "bundle_id": ns.bundle_id,
        "generated_at_utc": index["generated_at_utc"],
        "hash_algorithm": "sha256",
        "files": hash_entries,
    }

    index_path = bundle_dir / "index.json"
    manifest_path = bundle_dir / "hashes_sha256.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("WROTE:", index_path.resolve())
    print("WROTE:", manifest_path.resolve(), f"files={len(hash_entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
