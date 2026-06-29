#!/usr/bin/env python3
"""Oracle Logos Cursor-inject Tier-1 readiness chain ([HYPO] / B-track).

  py scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
REPORT = ROOT / "reports/logos_oracle_cursor_inject_tier1_readiness_chain_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-overlay-refresh", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    steps: list[dict] = []
    if not args.skip_overlay_refresh:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py",
                "--skip-pytest",
            ],
            cwd=ROOT,
            check=False,
        )
        steps.append({"step": "logos_math_overlay_chain", "exit_code": proc.returncode})
        if proc.returncode != 0:
            return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_cursor_inject_tier1_readiness_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "build_tier1_readiness", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/check_logos_track_a_miswire_guard_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "logos_track_a_miswire_guard", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    if not doc.get("tier1_module_ssot_ready"):
        print("FAIL: tier1_module_ssot_ready=false", file=sys.stderr)
        for row in doc.get("checks") or []:
            if not row.get("pass"):
                print(f"  FAIL: {row.get('check_id')} — {row.get('detail')}", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_oracle_cursor_inject_tier1_readiness_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    report = {
        "schema": "logos_oracle_cursor_inject_tier1_readiness_chain_v1",
        "chain_pass": True,
        "research_only": True,
        "tier1_module_ssot_ready": True,
        "tier2_cursor_full_upgrade_ready": False,
        "tier3_constitution_full_upgrade_ready": False,
        "readiness_artifact": str(OUT.relative_to(ROOT)),
        "steps": steps,
        "repro_one_shot": "py scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("chain_pass=true tier1_module_ssot_ready=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
