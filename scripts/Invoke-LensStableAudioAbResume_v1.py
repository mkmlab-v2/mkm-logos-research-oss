#!/usr/bin/env python3
"""Resume Stable Audio A/B: prereq probe -> smoke -> optional 12-pair bake -> stage."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(args: list[str]) -> int:
    print(f"[stable-ab-resume] {' '.join(args)}", flush=True)
    return subprocess.run(args, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full-matrix", action="store_true", help="After successful smoke, bake all 12 Stable Audio pairs")
    ap.add_argument("--deploy", action="store_true", help="Deploy showroom staging + sync VPS (default with deploy)")
    ap.add_argument("--no-sync-vps", action="store_true", help="Skip VPS sync after deploy")
    args = ap.parse_args()

    rc = _run([PY, "scripts/request_lens_stable_audio_hf_access_v1.py"])
    if rc != 0:
        print("[stable-ab-resume] WARN: ask-access skipped/failed — check token gated read + model Agree", flush=True)

    rc = _run([PY, "scripts/check_lens_stable_audio_prereqs_v1.py", "--probe-model"])
    hf_ok = rc == 0
    if not hf_ok:
        print("[stable-ab-resume] WARN: HF license not accepted — Stable side will tone-fallback", flush=True)

    rc = _run([PY, "scripts/run_lens_btrack_audio_generator_ab_smoke_v1.py", "--stable-steps", "50"])
    if rc != 0:
        print("[stable-ab-resume] WARN: both_ok=false (expected until HF license accepted)", flush=True)

    if args.full_matrix:
        rc = _run([PY, "scripts/build_lens_btrack_audio_loops_stable_audio_v1.py"])
        if rc != 0:
            return rc
        _run([PY, "scripts/normalize_lens_btrack_audio_loudness_v1.py"])

    rc = _run([PY, "scripts/stage_lens_btrack_audio_ab_smoke_for_showroom_v1.py"])
    if rc != 0:
        return rc

    if args.full_matrix:
        rc = _run([PY, "scripts/stage_lens_btrack_audio_stable_audio_for_showroom_v1.py"])
        if rc != 0:
            return rc

    if args.deploy:
        rc = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1",
            ]
        )
        if rc != 0:
            return rc
        if args.no_sync_vps:
            return 0
        return _run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/sync_showroom_to_vps.ps1",
                ]
            )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
