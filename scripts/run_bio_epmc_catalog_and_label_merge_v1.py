#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.55, K:0.7, M:0.4}
# Balance: 84
# Purpose: One-shot Europe PMC genetics catalog build plus PMID merge into consolidated_v3.
# Keywords: europepmc, catalog, merge, bio, pipeline, subprocess
"""Run catalog build then merge; optional paper SNP sidecar JSON export.

Catalog script receives any unknown CLI flags (e.g. ``--max-pages 1 --no-pmc-fallback``).
Wrapper-only flags: ``--with-sidecar``, ``--apply-sidecar-to-samples`` (+ paths; requires ``--with-sidecar``).
Optional precheck: ``--apply-mapping-coverage-min`` (>0 enables strict mapping coverage gate).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Chain: build_bio_epmc_sasang_genetics_catalog_v1.py then merge_bio_catalog_refsnp_into_measured_labels_v1.py.",
    )
    ap.add_argument(
        "--with-sidecar",
        action="store_true",
        help="After merge, run export_bio_measured_labels_paper_snp_sidecar_v1.py.",
    )
    ap.add_argument(
        "--apply-sidecar-to-samples",
        action="store_true",
        help="After sidecar export, join sidecar onto a cohort CSV (requires --with-sidecar).",
    )
    ap.add_argument("--apply-samples-csv", type=Path, default=None, help="Cohort CSV with sample_id.")
    ap.add_argument(
        "--apply-mapping-csv",
        type=Path,
        default=None,
        help="sample_id ↔ pmid (or paper_pmid) mapping CSV.",
    )
    ap.add_argument("--apply-output-csv", type=Path, default=None)
    ap.add_argument("--apply-output-report", type=Path, default=None)
    ap.add_argument(
        "--apply-mapping-coverage-min",
        type=float,
        default=0.0,
        metavar="RATIO",
        help="If >0, run mapping coverage strict precheck before apply; fails with exit 2 when below RATIO.",
    )
    ap.add_argument("--apply-coverage-output-json", type=Path, default=None)
    ap.add_argument(
        "--apply-skip-gate",
        action="store_true",
        help="Unsafe: pass --skip-gate to apply_bio_paper_snp_sidecar_to_samples_v1.py.",
    )
    args, unknown = ap.parse_known_args()
    catalog_args = list(unknown)

    if args.apply_sidecar_to_samples and not args.with_sidecar:
        print("--apply-sidecar-to-samples requires --with-sidecar.", file=sys.stderr)
        return 2
    if args.apply_sidecar_to_samples:
        if not args.apply_samples_csv or not args.apply_mapping_csv:
            print(
                "--apply-sidecar-to-samples requires --apply-samples-csv and --apply-mapping-csv.",
                file=sys.stderr,
            )
            return 2
        if args.apply_mapping_coverage_min < 0 or args.apply_mapping_coverage_min > 1:
            print("--apply-mapping-coverage-min must be between 0 and 1.", file=sys.stderr)
            return 1

    py = sys.executable
    build_cmd = [py, str(ROOT / "scripts" / "build_bio_epmc_sasang_genetics_catalog_v1.py")] + catalog_args
    merge_cmd = [py, str(ROOT / "scripts" / "merge_bio_catalog_refsnp_into_measured_labels_v1.py")]
    sidecar_cmd = [py, str(ROOT / "scripts" / "export_bio_measured_labels_paper_snp_sidecar_v1.py")]
    apply_script = ROOT / "scripts" / "apply_bio_paper_snp_sidecar_to_samples_v1.py"

    print("Step 1/2: build Europe PMC genetics catalog …", flush=True)
    subprocess.check_call(build_cmd, cwd=str(ROOT))
    print("Step 2/2: merge catalog RefSNPs into tmp/bio_measured_labels_consolidated_v3.csv …", flush=True)
    subprocess.check_call(merge_cmd, cwd=str(ROOT))
    if args.with_sidecar:
        print("Step 3: export paper SNP sidecar JSON …", flush=True)
        subprocess.check_call(sidecar_cmd, cwd=str(ROOT))
        if args.apply_sidecar_to_samples:
            cov_min = float(args.apply_mapping_coverage_min)
            if cov_min > 0:
                cov_cmd = [
                    py,
                    str(ROOT / "scripts" / "check_bio_paper_snp_mapping_coverage_v1.py"),
                    "--cohort-csv",
                    str(args.apply_samples_csv),
                    "--mapping-csv",
                    str(args.apply_mapping_csv),
                    "--min-coverage-ratio",
                    str(cov_min),
                    "--strict",
                ]
                if args.apply_coverage_output_json:
                    cov_cmd.extend(["--output-json", str(args.apply_coverage_output_json)])
                print(f"Step 4: mapping coverage precheck (min={cov_min}) …", flush=True)
                cr = subprocess.run(cov_cmd, cwd=str(ROOT))
                if cr.returncode != 0:
                    return cr.returncode
            apply_cmd = [
                py,
                str(apply_script),
                "--samples-csv",
                str(args.apply_samples_csv),
                "--mapping-csv",
                str(args.apply_mapping_csv),
            ]
            if args.apply_output_csv:
                apply_cmd.extend(["--output-csv", str(args.apply_output_csv)])
            if args.apply_output_report:
                apply_cmd.extend(["--output-report", str(args.apply_output_report)])
            if args.apply_skip_gate:
                apply_cmd.append("--skip-gate")
            print("Step 5: apply paper SNP sidecar to cohort rows …", flush=True)
            ar = subprocess.run(apply_cmd, cwd=str(ROOT))
            if ar.returncode != 0:
                return ar.returncode
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
