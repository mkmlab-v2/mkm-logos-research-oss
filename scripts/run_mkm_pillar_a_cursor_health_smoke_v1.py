#!/usr/bin/env python3
"""Pillar A Cursor continuity health smoke — audit + bench + diet strict."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS: list[tuple[str, list[str]]] = [
    (
        "turn_meta_audit",
        [sys.executable, "scripts/check_mkm_cursor_turn_meta_audit_v1.py"],
    ),
    (
        "continuity_bench",
        [sys.executable, "scripts/run_mkm_cursor_continuity_bench_v1.py", "--lane", "infra"],
    ),
    (
        "route_bench",
        [sys.executable, "scripts/bench_mkm_ltm_route_accuracy_v1.py"],
    ),
    (
        "context_diet_strict",
        [sys.executable, "scripts/check_cursor_rules_context_diet_v1.py", "--strict"],
    ),
]


def _run(label: str, cmd: list[str], *, dry_run: bool) -> int:
    rel = " ".join(cmd[1:] if cmd and cmd[0] == sys.executable else cmd)
    if dry_run:
        print(f"DRY: {label}: py {rel}")
        return 0
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        print(f"FAIL: {label} exit {proc.returncode}", file=sys.stderr)
    else:
        print(f"OK: {label}")
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--skip-continuity", action="store_true")
    parser.add_argument("--skip-route", action="store_true")
    parser.add_argument("--skip-diet", action="store_true")
    args = parser.parse_args(argv)

    skip = {
        "turn_meta_audit": args.skip_audit,
        "continuity_bench": args.skip_continuity,
        "route_bench": args.skip_route,
        "context_diet_strict": args.skip_diet,
    }

    for label, cmd in STEPS:
        if skip.get(label):
            print(f"SKIP: {label}")
            continue
        code = _run(label, cmd, dry_run=args.dry_run)
        if code != 0:
            return code

    print("OK: pillar_a_cursor_health_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
