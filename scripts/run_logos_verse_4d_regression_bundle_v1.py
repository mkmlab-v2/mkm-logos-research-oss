#!/usr/bin/env python3
"""Unified pytest regression entry for logos verse 4D Track B stack.

Collects tests matching:
  test_logos_verse_4d*
  test_build_logos_verse_canon_coverage*
  test_project_logos_verse*
  test_build_logos_verse_4d_showroom* (if present)

Exit 0 only when all collected tests pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

TEST_GLOBS = (
    "test_logos_verse_4d*.py",
    "test_logos_textual_variant_distance_v1.py",
    "test_logos_multi_orbit_chain_v1.py",
    "test_logos_nt_adjacent_verse_v1.py",
    "test_logos_satellite_dev_chain_v1.py",
    "test_logos_tr_osis_to_mt_verse_v1.py",
    "test_build_logos_tr_variant_vectors_v1.py",
    "test_build_logos_tr_nt_corpus_manifest_v1.py",
    "test_logos_tr_scrollmapper_crossval_v1.py",
    "test_build_logos_dss_enriched_manifest_v1.py",
    "test_build_logos_dss_satellite_lane_v1.py",
    "test_build_logos_satellite_knn_drift_pack_v1.py",
    "test_build_logos_dss_crossref_slot_mapping_v1.py",
    "test_build_logos_dss_crossref_strict_gate_audit_v1.py",
    "test_build_logos_dss_slot_mapping_refresh_pack_v1.py",
    "test_dss_direct_slot_mapping.py",
    "test_build_logos_verse_canon_coverage*.py",
    "test_project_logos_verse*.py",
    "test_build_logos_verse_4d_showroom*.py",
    "test_build_logos_verse_myeongri_cross_bridge*.py",
    "test_build_logos_b2b_verse_4d*.py",
)


def _collect_test_files() -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in TEST_GLOBS:
        for path in sorted(TESTS_DIR.glob(pattern)):
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            files.append(path)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Run logos verse 4D Track B pytest regression bundle.")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List collected test files and pytest command without executing.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable summary on stdout (still runs pytest unless --dry-run).",
    )
    args = ap.parse_args()

    test_files = _collect_test_files()
    if not test_files:
        print("ERROR: no logos verse 4D regression test files matched", file=sys.stderr, flush=True)
        return 2

    rel_paths = [str(p.relative_to(ROOT)).replace("\\", "/") for p in test_files]
    cmd = [sys.executable, "-m", "pytest", *rel_paths, "-q", "--tb=short"]

    if args.dry_run:
        payload = {"dry_run": True, "test_files": rel_paths, "pytest_cmd": cmd}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
        else:
            print(f"DRY_RUN: would run {len(rel_paths)} test file(s)")
            for rel in rel_paths:
                print(f"  - {rel}")
            print("pytest:", " ".join(cmd))
        return 0

    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if cp.stdout:
        print(cp.stdout, end="" if cp.stdout.endswith("\n") else "\n", flush=True)
    if cp.stderr:
        print(cp.stderr, end="" if cp.stderr.endswith("\n") else "\n", file=sys.stderr, flush=True)

    if args.json:
        summary = {
            "dry_run": False,
            "exit_code": int(cp.returncode),
            "test_files": rel_paths,
            "pytest_cmd": cmd,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
