#!/usr/bin/env python3
"""B-track Multi-Orbit chain: MT-only classify → textual variant → satellite drift → showroom pack."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-classify", action="store_true")
    ap.add_argument("--skip-textual-variant", action="store_true")
    ap.add_argument("--skip-drift-metrics", action="store_true")
    ap.add_argument("--skip-orbit-drift", action="store_true")
    ap.add_argument("--skip-showroom-pack", action="store_true")
    ap.add_argument("--skip-tr-scaffold", action="store_true")
    ap.add_argument("--skip-tr-ingest", action="store_true")
    ap.add_argument("--skip-tr-download", action="store_true", help="Use cached honza JSON only.")
    ap.add_argument(
        "--full-nt-tr",
        action="store_true",
        help="Also write data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl + manifest.",
    )
    ap.add_argument("--include-satellite-dev", action="store_true")
    ap.add_argument("--include-shared-vault-dss", action="store_true")
    ap.add_argument(
        "--include-slot-mapping-refresh",
        action="store_true",
        help="Forward to satellite dev chain: full vs canonical slot mapping refresh.",
    )
    ap.add_argument("--force-apocrypha-bootstrap", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = []

    if not args.skip_classify:
        steps.append(
            (
                "mt_only_residual_classify",
                [py, str(ROOT / "scripts/build_logos_gap_mt_only_residual_classify_v1.py")],
            )
        )
    if not args.skip_tr_ingest:
        ingest_cmd = [
            py,
            str(ROOT / "scripts/ingest_tr_greek_from_honza_v1.py"),
            "--gap-only",
        ]
        if args.skip_tr_download:
            ingest_cmd.append("--skip-download")
        steps.append(("tr_greek_ingest", ingest_cmd))
        if args.full_nt_tr:
            full_cmd = [
                py,
                str(ROOT / "scripts/ingest_tr_greek_from_honza_v1.py"),
                "--full-nt",
                "--output",
                str(ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl"),
            ]
            if args.skip_tr_download:
                full_cmd.append("--skip-download")
            steps.append(("tr_greek_full_nt", full_cmd))
            steps.append(
                (
                    "tr_nt_manifest",
                    [py, str(ROOT / "scripts/build_logos_tr_nt_corpus_manifest_v1.py")],
                )
            )
        steps.append(
            (
                "tr_variant_vectors",
                [py, str(ROOT / "scripts/build_logos_tr_variant_vectors_v1.py")],
            )
        )
    if not args.skip_textual_variant:
        steps.append(
            (
                "textual_variant_distance",
                [py, str(ROOT / "scripts/build_logos_textual_variant_distance_v1.py")],
            )
        )
    if not args.skip_drift_metrics:
        steps.append(
            (
                "satellite_drift_metrics",
                [py, str(ROOT / "scripts/build_logos_satellite_drift_metrics_v1.py")],
            )
        )
    if not args.skip_orbit_drift:
        steps.append(
            (
                "satellite_orbit_drift",
                [py, str(ROOT / "scripts/build_logos_satellite_orbit_drift_v1.py")],
            )
        )
    if not args.skip_tr_scaffold:
        steps.append(
            (
                "tr_tradition_scaffold",
                [
                    py,
                    str(ROOT / "scripts/build_logos_tr_tradition_scaffold_v1.py"),
                    "--write-manifest-dir",
                ],
            )
        )
    if args.include_satellite_dev:
        sat_cmd = [py, str(ROOT / "scripts/run_logos_satellite_dev_chain_v1.py")]
        if args.force_apocrypha_bootstrap:
            sat_cmd.append("--force-apocrypha-bootstrap")
        if args.include_shared_vault_dss:
            sat_cmd.append("--include-shared-vault-dss")
        if args.include_slot_mapping_refresh:
            sat_cmd.append("--include-slot-mapping-refresh")
        steps.append(("satellite_dev", sat_cmd))
    if not args.skip_showroom_pack:
        steps.append(
            (
                "multi_orbit_showroom_pack",
                [py, str(ROOT / "scripts/build_logos_multi_orbit_showroom_pack_v1.py")],
            )
        )
        steps.append(
            (
                "b2b_multi_orbit_appendix",
                [py, str(ROOT / "scripts/build_logos_b2b_multi_orbit_appendix_v1.py")],
            )
        )

    for name, cmd in steps:
        print(f"[multi-orbit] {name}", flush=True)
        rc = _run(cmd)
        if rc != 0:
            return rc
    print("[multi-orbit] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
