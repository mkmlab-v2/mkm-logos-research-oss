#!/usr/bin/env python3
"""Extended Multi-Orbit research chain: TR full-NT + scrollmapper crossval + DSS enriched + multi-orbit."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"


def _run(cmd: list[str]) -> int:
    print(" ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-full-nt-ingest", action="store_true")
    ap.add_argument("--skip-scrollmapper-crossval", action="store_true")
    ap.add_argument("--skip-scrollmapper-download", action="store_true")
    ap.add_argument("--skip-dss-enriched", action="store_true")
    ap.add_argument(
        "--include-slot-mapping-refresh",
        action="store_true",
        help="After DSS lane: full vs canonical slot mapping refresh + strict gate audit.",
    )
    ap.add_argument(
        "--include-shared-vault-dss",
        action="store_true",
        help="Also scan G: MKM_DATA_VAULT for DSS markdown when rebuilding enriched JSONL.",
    )
    ap.add_argument("--skip-multi-orbit", action="store_true")
    ap.add_argument("--force-apocrypha-bootstrap", action="store_true")
    args = ap.parse_args()

    py = sys.executable

    if not args.skip_full_nt_ingest:
        rc = _run(
            [
                py,
                str(ROOT / "scripts/ingest_tr_greek_from_honza_v1.py"),
                "--full-nt",
                "--skip-download",
                "--output",
                str(ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.full_nt.jsonl"),
            ]
        )
        if rc != 0:
            return rc
        rc = _run([py, str(ROOT / "scripts/build_logos_tr_nt_corpus_manifest_v1.py")])
        if rc != 0:
            return rc

    if not args.skip_scrollmapper_crossval:
        cross_cmd = [
            py,
            str(ROOT / "scripts/build_logos_tr_scrollmapper_crossval_v1.py"),
        ]
        if args.skip_scrollmapper_download:
            cross_cmd.append("--skip-download")
        rc = _run(cross_cmd)
        if rc != 0:
            return rc

    if not args.skip_dss_enriched:
        dss_cmd = [
            py,
            str(ROOT / "scripts/build_btrack_dss_enriched_from_docs.py"),
            "--require-evidence-keyword",
        ]
        if args.include_shared_vault_dss:
            dss_cmd.append("--include-shared-vault")
        rc = _run(dss_cmd)
        if rc != 0:
            return rc
        rc = _run([py, str(ROOT / "scripts/build_logos_dss_enriched_manifest_v1.py")])
        if rc != 0:
            return rc
        rc = _run([py, str(ROOT / "scripts/build_logos_dss_satellite_lane_v1.py")])
        if rc != 0:
            return rc
        rc = _run([py, str(ROOT / "scripts/report_dss_4d_projection.py")])
        if rc != 0:
            return rc
        rc = _run([py, str(ROOT / "scripts/build_logos_dss_crossref_slot_mapping_v1.py")])
        if rc != 0:
            return rc
        if args.include_slot_mapping_refresh:
            rc = _run([py, str(ROOT / "scripts/build_logos_dss_slot_mapping_refresh_pack_v1.py")])
            if rc != 0:
                return rc

    if not args.skip_multi_orbit:
        cmd = [
            py,
            str(ROOT / "scripts/run_logos_multi_orbit_chain_v1.py"),
            "--include-satellite-dev",
            "--skip-tr-download",
        ]
        if args.include_shared_vault_dss:
            cmd.append("--include-shared-vault-dss")
        if args.include_slot_mapping_refresh:
            cmd.append("--include-slot-mapping-refresh")
        if args.force_apocrypha_bootstrap:
            cmd.append("--force-apocrypha-bootstrap")
        rc = _run(cmd)
        if rc != 0:
            return rc

    if CROSS_REF.is_file():
        print(f"[research] cross_ref_present {CROSS_REF}", flush=True)
    else:
        print(f"[research] WARN missing {CROSS_REF} — restore from git or build_cross_ref", flush=True)

    print("[research] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
