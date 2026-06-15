#!/usr/bin/env python3
"""One-click zone_f_code template catalog pipeline: batch extract → coverage → merge plan.

Does NOT apply production merge unless --human-approve-merge --reviewer are set.
research_only · SEND_GATE HOLD.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
    else:
        print(proc.stdout.strip())
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="zone_f_code catalog pipeline")
    ap.add_argument("--write-prospect", action="store_true")
    ap.add_argument("--human-approve-merge", action="store_true")
    ap.add_argument("--reviewer", default=None)
    ap.add_argument("--rebuild-gate", action="store_true")
    args = ap.parse_args()
    py = sys.executable
    steps: list[list[str]] = [
        [py, "scripts/run_zone_f_code_template_catalog_batch_extract_v1.py"]
        + (["--write-prospect"] if args.write_prospect else []),
        [py, "scripts/run_zone_f_code_template_catalog_coverage_v1.py"],
        [py, "scripts/merge_zone_f_code_template_prospect_to_catalog_v1.py"],
    ]
    if args.human_approve_merge:
        if not args.reviewer:
            print("DENIED: --human-approve-merge requires --reviewer", file=sys.stderr)
            return 2
        merge_cmd = [
            py,
            "scripts/merge_zone_f_code_template_prospect_to_catalog_v1.py",
            "--human-approve-merge",
            "--reviewer",
            str(args.reviewer),
        ]
        if args.rebuild_gate:
            merge_cmd.append("--rebuild-gate")
        steps.append(merge_cmd)
    for cmd in steps:
        if _run(cmd) != 0:
            return 1
    print(json.dumps({"ok": True, "pipeline": "zone_f_code_template_catalog_v1"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
