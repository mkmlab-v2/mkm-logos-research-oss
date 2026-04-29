#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.85, L:0.7, K:0.8, M:0.48}
# Balance: 88
# Purpose: Chain PDF spike extraction -> PMID/rsID sidecar build -> optional sample join apply.
# Keywords: bio, pdf, sidecar, chain, pmid, rsid, apply
"""Run end-to-end chain: PDF -> JSONL -> SNP sidecar -> optional apply to samples."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print("RUN:", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Chain PDF spike outputs into bio SNP sidecar and optional sample join.",
    )
    ap.add_argument("--input-pdf", type=Path, nargs="+", required=True)
    ap.add_argument(
        "--spike-output-dir",
        type=Path,
        default=Path("tmp/pdf_spike_chain_v1"),
    )
    ap.add_argument(
        "--spike-output-jsonl",
        type=Path,
        default=Path("tmp/pdf_spike_chain_v1/pdf_spike_rows_latest.jsonl"),
    )
    ap.add_argument(
        "--spike-output-report",
        type=Path,
        default=Path("reports/pdf_spike_chain_benchmark_v1_latest.json"),
    )
    ap.add_argument(
        "--sidecar-output-json",
        type=Path,
        default=Path("tmp/bio_measured_labels_paper_snp_sidecar_from_pdf_chain_v1.json"),
    )
    ap.add_argument(
        "--sidecar-doc-map-csv",
        type=Path,
        default=Path("tmp/bio_pdf_doc_pmid_map_chain_v1.csv"),
    )
    ap.add_argument(
        "--min-rsid-per-paper",
        type=int,
        default=1,
    )
    ap.add_argument("--samples-csv", type=Path, default=None)
    ap.add_argument("--mapping-csv", type=Path, default=None)
    ap.add_argument(
        "--apply-output-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_pdf_sidecar_chain_v1.csv"),
    )
    ap.add_argument(
        "--apply-output-report",
        type=Path,
        default=Path("reports/bio_pdf_sidecar_chain_apply_v1_latest.json"),
    )
    ns = ap.parse_args()

    missing = [str(p) for p in ns.input_pdf if not p.is_file()]
    if missing:
        print(f"missing input PDF(s): {missing}", file=sys.stderr)
        return 1

    py = sys.executable

    # 1) PDF -> JSONL spike
    spike_cmd = [
        py,
        str(ROOT / "scripts" / "run_pdf_to_jsonl_spike_v1.py"),
        "--input-pdf",
        *[str(p) for p in ns.input_pdf],
        "--output-dir",
        str(ns.spike_output_dir),
        "--output-jsonl",
        str(ns.spike_output_jsonl),
        "--output-report",
        str(ns.spike_output_report),
    ]
    rc = _run(spike_cmd)
    if rc != 0:
        return rc

    # 2) JSONL -> sidecar
    sidecar_cmd = [
        py,
        str(ROOT / "scripts" / "build_bio_paper_snp_sidecar_from_pdf_jsonl_v1.py"),
        "--input-jsonl",
        str(ns.spike_output_jsonl),
        "--output-json",
        str(ns.sidecar_output_json),
        "--output-doc-map-csv",
        str(ns.sidecar_doc_map_csv),
        "--min-rsid-per-paper",
        str(ns.min_rsid_per_paper),
    ]
    rc = _run(sidecar_cmd)
    if rc != 0:
        return rc

    # 3) Optional apply to samples.
    if ns.samples_csv and ns.mapping_csv:
        apply_cmd = [
            py,
            str(ROOT / "scripts" / "apply_bio_paper_snp_sidecar_to_samples_v1.py"),
            "--samples-csv",
            str(ns.samples_csv),
            "--mapping-csv",
            str(ns.mapping_csv),
            "--sidecar-json",
            str(ns.sidecar_output_json),
            "--output-csv",
            str(ns.apply_output_csv),
            "--output-report",
            str(ns.apply_output_report),
        ]
        rc = _run(apply_cmd)
        if rc != 0:
            return rc

    print("DONE: bio_pdf_sidecar_chain_v1", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
