#!/usr/bin/env python3
"""Post commander signoff: record JSON, refresh pointers, smoke pytest, bundle summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = ROOT / "docs/final/artifacts/rq021_commander_btrack_signoff_v1_latest.json"
BUNDLE_OUT = ROOT / "reports/rq021_post_signoff_bundle_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 post signoff routine")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec = _run([sys.executable, str(ROOT / "scripts/record_rq021_commander_btrack_signoff_v1.py")])
    steps.append({"step": "record_signoff", "exit_code": ec})
    if ec != 0:
        _write(steps, ok=False)
        return ec

    ec = _run([sys.executable, str(ROOT / "scripts/build_master_codebook_bench_lexicon_pointer_v1.py")])
    steps.append({"step": "codebook_pointer", "exit_code": ec})

    ec = _run([sys.executable, str(ROOT / "scripts/build_golden40_expansion_per_lane_report_v1.py")])
    steps.append({"step": "per_lane_report_refresh", "exit_code": ec})

    if not args.skip_pytest:
        ec = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_golden40_hypo_cooc_sidecar_v1.py",
                "tests/test_run_other_cooc_cartesian_routing_poc_v2.py",
                "tests/test_run_polar_coord_compression_hypo_v3.py",
                "-q",
            ]
        )
        steps.append({"step": "pytest_smoke", "exit_code": ec})

    signoff = json.loads(SIGNOFF.read_text(encoding="utf-8")) if SIGNOFF.is_file() else {}
    _write(steps, ok=True, signoff=signoff)
    print(f"OK: {BUNDLE_OUT}")
    return 0


def _write(steps: list[dict[str, Any]], *, ok: bool, signoff: dict[str, Any] | None = None) -> None:
    doc = {
        "schema": "rq021_post_signoff_bundle_v1",
        "generated_at_utc": _utc(),
        "routine_ok": ok,
        "steps": steps,
        "signoff": signoff,
        "operating_ssot": {
            "signoff": "docs/final/artifacts/rq021_commander_btrack_signoff_v1_latest.json",
            "per_lane_report": "reports/golden40_expansion_per_lane_report_v1_latest.json",
            "dryrun_example": "reports/golden_40_expansion_dryrun_rq021_mixed_cooc_v2_latest.json",
        },
    }
    BUNDLE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
