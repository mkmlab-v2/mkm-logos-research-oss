#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.82, L:0.6, K:0.78, M:0.42}
# Balance: 86
# Purpose: No-EPMC chain: export paper SNP sidecar JSON from consolidated v3, then apply to sample rows.
# Keywords: bio, SNP, sidecar, export, apply, chain
"""Run export_bio_measured_labels_paper_snp_sidecar then apply_bio_paper_snp_sidecar_to_samples (no Europe PMC)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Chain: paper SNP sidecar JSON export, then join onto cohort (constitution-gated).",
    )
    ap.add_argument(
        "--skip-export",
        action="store_true",
        help="Only run apply; use existing --sidecar-json (e.g. after manual copy).",
    )
    ap.add_argument(
        "--input-csv",
        type=Path,
        default=Path("tmp/bio_measured_labels_consolidated_v3.csv"),
        help="Input to export script (ignored with --skip-export).",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/final/artifacts/bio_measured_labels_paper_snp_sidecar_v1.json"),
        help="Sidecar JSON from export; default input to apply unless --sidecar-json is set.",
    )
    ap.add_argument(
        "--sidecar-json",
        type=Path,
        default=None,
        help="Override sidecar path for apply (default: same as --output-json).",
    )
    ap.add_argument("--samples-csv", type=Path, required=True)
    ap.add_argument("--mapping-csv", type=Path, required=True)
    ap.add_argument(
        "--output-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_paper_snp_sidecar_v1.csv"),
    )
    ap.add_argument(
        "--output-report",
        type=Path,
        default=Path("reports/bio_paper_snp_sidecar_sample_join_v1_latest.json"),
    )
    ap.add_argument(
        "--skip-gate",
        action="store_true",
        help="Unsafe: pass through to apply script.",
    )
    ap.add_argument(
        "--mapping-coverage-min",
        type=float,
        default=0.0,
        metavar="RATIO",
        help="If >0, run check_bio_paper_snp_mapping_coverage_v1.py with --strict before apply; exit 2 if below RATIO (0..1).",
    )
    ap.add_argument(
        "--coverage-output-json",
        type=Path,
        default=None,
        help="Report path for mapping coverage check (default: reports/bio_paper_snp_mapping_coverage_v1_latest.json).",
    )
    ns = ap.parse_args()

    if not ns.samples_csv.is_file():
        print(f"missing --samples-csv: {ns.samples_csv}", file=sys.stderr)
        return 1
    if not ns.mapping_csv.is_file():
        print(f"missing --mapping-csv: {ns.mapping_csv}", file=sys.stderr)
        return 1

    sidecar = ns.sidecar_json or ns.output_json
    py = sys.executable

    cov_min = float(ns.mapping_coverage_min)
    if cov_min < 0 or cov_min > 1:
        print("--mapping-coverage-min must be between 0 and 1", file=sys.stderr)
        return 1
    if cov_min > 0:
        cov_out = ns.coverage_output_json or Path("reports/bio_paper_snp_mapping_coverage_v1_latest.json")
        check_cmd = [
            py,
            str(ROOT / "scripts" / "check_bio_paper_snp_mapping_coverage_v1.py"),
            "--cohort-csv",
            str(ns.samples_csv),
            "--mapping-csv",
            str(ns.mapping_csv),
            "--output-json",
            str(cov_out),
            "--min-coverage-ratio",
            str(cov_min),
            "--strict",
        ]
        print(f"Precheck: mapping coverage (min={cov_min}) …", flush=True)
        cr = subprocess.run(check_cmd, cwd=str(ROOT))
        if cr.returncode != 0:
            return cr.returncode

    export_cmd = [
        py,
        str(ROOT / "scripts" / "export_bio_measured_labels_paper_snp_sidecar_v1.py"),
        "--input-csv",
        str(ns.input_csv),
        "--output-json",
        str(ns.output_json),
    ]
    apply_cmd = [
        py,
        str(ROOT / "scripts" / "apply_bio_paper_snp_sidecar_to_samples_v1.py"),
        "--samples-csv",
        str(ns.samples_csv),
        "--sidecar-json",
        str(sidecar),
        "--mapping-csv",
        str(ns.mapping_csv),
        "--output-csv",
        str(ns.output_csv),
        "--output-report",
        str(ns.output_report),
    ]
    if ns.skip_gate:
        apply_cmd.append("--skip-gate")

    if not ns.skip_export:
        if not ns.input_csv.is_file():
            print(f"missing --input-csv: {ns.input_csv}", file=sys.stderr)
            return 1
        print("Step 1/2: export paper SNP sidecar JSON …", flush=True)
        er = subprocess.run(export_cmd, cwd=str(ROOT))
        if er.returncode != 0:
            return er.returncode
    else:
        if not sidecar.is_file():
            print(f"missing sidecar (--sidecar-json / --output-json): {sidecar}", file=sys.stderr)
            return 1

    print(
        "Step 2/2: apply sidecar to samples …"
        if not ns.skip_export
        else "Apply: join sidecar onto samples (--skip-export) …",
        flush=True,
    )
    ar = subprocess.run(apply_cmd, cwd=str(ROOT))
    if ar.returncode != 0:
        return ar.returncode
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
