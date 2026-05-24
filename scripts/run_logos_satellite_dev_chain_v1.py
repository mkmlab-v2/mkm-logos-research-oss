#!/usr/bin/env python3
"""Satellite dev chain: apocrypha + DSS lanes → kNN pack → orbit refresh."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON_CORPUS = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_single_anchor_v1_latest.jsonl"


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force-apocrypha-bootstrap", action="store_true")
    ap.add_argument("--import-apocrypha-jsonl", type=Path, default=None)
    ap.add_argument("--skip-bootstrap", action="store_true")
    ap.add_argument("--skip-apocrypha-lane", action="store_true")
    ap.add_argument("--skip-dss-lane", action="store_true")
    ap.add_argument("--skip-dss-projection", action="store_true")
    ap.add_argument("--skip-dss-slot-mapping", action="store_true")
    ap.add_argument(
        "--include-slot-mapping-refresh",
        action="store_true",
        help="Full vs canonical-only mapping refresh + comparison + strict gate audit.",
    )
    ap.add_argument("--skip-knn", action="store_true")
    ap.add_argument("--skip-orbit-refresh", action="store_true")
    ap.add_argument(
        "--include-shared-vault-dss",
        action="store_true",
        help="Rebuild DSS enriched from docs + G: vault before lane projection.",
    )
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = []

    if not args.skip_bootstrap:
        boot = [py, str(ROOT / "scripts/bootstrap_logos_apocrypha_manuscript_jsonl_v1.py")]
        if args.force_apocrypha_bootstrap:
            boot.append("--force")
        if args.import_apocrypha_jsonl:
            boot.extend(["--import-jsonl", str(args.import_apocrypha_jsonl)])
        steps.append(("apocrypha_bootstrap", boot))

    if not args.skip_apocrypha_lane:
        steps.append(
            (
                "apocrypha_lane",
                [
                    py,
                    str(ROOT / "scripts/build_logos_verse_4d_null_corpus_v1.py"),
                    "--input-jsonl",
                    str(CANON_CORPUS),
                    "--skip-vector-permutation",
                    "--skip-char-shuffle",
                    "--skip-token-shuffle",
                ],
            )
        )

    if args.include_shared_vault_dss:
        dss_build = [
            py,
            str(ROOT / "scripts/build_btrack_dss_enriched_from_docs.py"),
            "--require-evidence-keyword",
            "--include-shared-vault",
        ]
        steps.insert(0, ("dss_enriched_vault", dss_build))

    if not args.skip_dss_lane:
        steps.append(("dss_enriched_manifest", [py, str(ROOT / "scripts/build_logos_dss_enriched_manifest_v1.py")]))
        steps.append(("dss_satellite_lane", [py, str(ROOT / "scripts/build_logos_dss_satellite_lane_v1.py")]))

    if not args.skip_dss_projection:
        steps.append(("dss_4d_projection", [py, str(ROOT / "scripts/report_dss_4d_projection.py")]))

    if not args.skip_dss_slot_mapping:
        steps.append(
            ("dss_crossref_slot_mapping", [py, str(ROOT / "scripts/build_logos_dss_crossref_slot_mapping_v1.py")])
        )

    if args.include_slot_mapping_refresh:
        steps.append(
            (
                "dss_slot_mapping_refresh_pack",
                [py, str(ROOT / "scripts/build_logos_dss_slot_mapping_refresh_pack_v1.py")],
            )
        )

    if not args.skip_knn:
        steps.append(
            (
                "satellite_knn_drift_pack",
                [py, str(ROOT / "scripts/build_logos_satellite_knn_drift_pack_v1.py")],
            )
        )

    if not args.skip_orbit_refresh:
        steps.append(
            (
                "satellite_orbit_drift",
                [py, str(ROOT / "scripts/build_logos_satellite_orbit_drift_v1.py")],
            )
        )

    for name, cmd in steps:
        print(f"[satellite-dev] {name}", flush=True)
        rc = _run(cmd)
        if rc != 0:
            return rc
    print("[satellite-dev] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
