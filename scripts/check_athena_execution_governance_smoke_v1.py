#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke checks for Athena execution governance (§28).

Verifies scripts exist, ``athena_doctor_v1`` runs, and HOLD governance denies
``TRADE_EXECUTE`` with exit code 2 (no webhook POST; temp audit/ecc paths).

Exit 0 = OK. Exit 1 = failure.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _must_exist(p: Path, label: str) -> None:
    if not p.is_file():
        raise SystemExit(f"check_athena_execution_governance_smoke_v1: missing {label}: {p}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Athena §28 governance smoke checks.")
    ap.add_argument("--quiet", action="store_true", help="Only print on failure.")
    args = ap.parse_args()

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    scripts = [
        ("athena_run_v1", WORKSPACE_ROOT / "scripts" / "athena_run_v1.py"),
        ("athena_doctor_v1", WORKSPACE_ROOT / "scripts" / "athena_doctor_v1.py"),
        ("athena_ecc_logs_v1", WORKSPACE_ROOT / "scripts" / "athena_ecc_logs_v1.py"),
        ("hold_fixture", WORKSPACE_ROOT / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"),
        ("trade_dummy", WORKSPACE_ROOT / "scripts" / "trade_dummy.py"),
    ]
    for label, path in scripts:
        _must_exist(path, label)

    log("check_athena_execution_governance_smoke_v1: doctor …")
    doc = subprocess.run(
        [sys.executable, str(WORKSPACE_ROOT / "scripts" / "athena_doctor_v1.py")],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    if doc.returncode != 0:
        print(doc.stderr or doc.stdout, file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        ecc_out = td_path / "ecc.json"
        audit = td_path / "audit.jsonl"
        log("check_athena_execution_governance_smoke_v1: HOLD deny path …")
        proc = subprocess.run(
            [
                sys.executable,
                str(WORKSPACE_ROOT / "scripts" / "athena_run_v1.py"),
                "--governance-json",
                str(WORKSPACE_ROOT / "scripts" / "fixtures" / "integrated_governance_v1_hold.json"),
                "--ecc-out",
                str(ecc_out),
                "--audit-jsonl",
                str(audit),
                "--no-audit-append",
                "--no-audit-webhook",
                "--",
                sys.executable,
                str(WORKSPACE_ROOT / "scripts" / "trade_dummy.py"),
            ],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 2:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            print(f"expected exit 2, got {proc.returncode}", file=sys.stderr)
            return 1
        if "ECC DENIED" not in (proc.stderr or ""):
            print("missing ECC DENIED on stderr", file=sys.stderr)
            return 1

    log("check_athena_execution_governance_smoke_v1: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
