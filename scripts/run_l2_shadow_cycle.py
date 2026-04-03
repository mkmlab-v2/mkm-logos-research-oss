#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run one L2 shadow cycle:
1) Build latest L2 shadow bundle
2) Verify readiness gates
3) Write cycle status artifact
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    wr = _workspace_root()
    ap = argparse.ArgumentParser(description="Run L2 shadow cycle (build + verify).")
    ap.add_argument("--episode-id", default="mkt_2020-03_covid_shock_v1")
    ap.add_argument("--track-a-status", choices=("pending", "ok"), default="ok")
    ap.add_argument(
        "--track-a-pointer",
        action="append",
        default=[
            "docs/final/artifacts/logos_independent_lens_latest.json",
            "docs/final/LOGOS_RISK_BRIDGE_v1.md",
        ],
    )
    ap.add_argument(
        "--track-b-pointer",
        action="append",
        default=[
            "docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
            "docs/final/artifacts/blind_replay_regime_conditional_selection_latest.json",
            "reports/memory/mkm_index_drift_audit_latest.json",
        ],
    )
    ap.add_argument("--primary-regime-narrative", default="covid_shock_context_label_only")
    ap.add_argument("--out-dir", type=Path, default=wr / "reports" / "l2")
    args = ap.parse_args()

    build_cmd = [
        sys.executable,
        str(wr / "scripts" / "build_l2_logos_shadow_bundle.py"),
        "--episode-id",
        args.episode_id,
        "--track-a-status",
        args.track_a_status,
        "--primary-regime-narrative",
        args.primary_regime_narrative,
        "--out-dir",
        str(args.out_dir),
        "--require-existing-pointers",
    ]
    for p in args.track_a_pointer:
        build_cmd += ["--track-a-pointer", p]
    for p in args.track_b_pointer:
        build_cmd += ["--track-b-pointer", p]

    build = _run(build_cmd, wr)
    verify = _run([sys.executable, str(wr / "scripts" / "verify_l2_shadow_readiness.py")], wr)

    status = {
        "timestamp_utc": _utc_stamp(),
        "build_exit_code": int(build.returncode),
        "verify_exit_code": int(verify.returncode),
        "all_green": bool(build.returncode == 0 and verify.returncode == 0),
        "build_stdout_tail": build.stdout[-4000:],
        "build_stderr_tail": build.stderr[-4000:],
        "verify_stdout_tail": verify.stdout[-4000:],
        "verify_stderr_tail": verify.stderr[-4000:],
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = status["timestamp_utc"]
    out = args.out_dir / f"l2_shadow_cycle_status_{stamp}.json"
    latest = args.out_dir / "l2_shadow_cycle_status_latest.json"
    payload = json.dumps(status, ensure_ascii=False, indent=2)
    out.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")

    print(payload)
    print(f"Wrote: {out}")
    print(f"Wrote: {latest}")
    return 0 if status["all_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
