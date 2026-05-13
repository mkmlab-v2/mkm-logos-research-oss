#!/usr/bin/env python3
"""Run build_integrated_governance_v1.py when config + three KOSPI gate JSONs exist.

Exits 0 with a SKIP line if any dependency is missing (host chains must not fail).
Otherwise runs the builder; by default passes ``--validate-digest-schema``.

Usage:
  py scripts/invoke_build_integrated_governance_if_deps_present_v1.py
  py scripts/invoke_build_integrated_governance_if_deps_present_v1.py --skip-digest-schema-validation
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _deps(root: Path) -> list[Path]:
    art = root / "docs" / "final" / "artifacts"
    return [
        art / "integrated_governance_config_v1.json",
        art / "kospi_biblical_single_lane_commercial_gate_v1_latest.json",
        art / "kospi_myeongri_standalone_commercial_gate_v1_latest.json",
        art / "kospi_sasang_single_lane_commercial_gate_v1_latest.json",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrated governance builder when deps exist.")
    ap.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of scripts/).",
    )
    ap.add_argument(
        "--skip-digest-schema-validation",
        action="store_true",
        help="Do not pass --validate-digest-schema to the builder.",
    )
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    missing = [p for p in _deps(root) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"[integrated-governance] SKIP: missing dependency: {p}", file=sys.stderr)
        return 0

    builder = root / "scripts" / "build_integrated_governance_v1.py"
    if not builder.is_file():
        print(f"invoke_build_integrated_governance_if_deps_present_v1: missing {builder}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(builder)]
    if not args.skip_digest_schema_validation:
        cmd.append("--validate-digest-schema")
    print("[integrated-governance] " + " ".join(cmd[1:]), flush=True)
    r = subprocess.run(cmd, cwd=str(root))
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
