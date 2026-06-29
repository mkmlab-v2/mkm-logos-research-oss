#!/usr/bin/env python3
"""One-shot Layer-1-only Brier bench PoC chain: register -> probe -> eval (B rail)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGISTER = ROOT / "scripts" / "register_layer1_only_brier_bench_poc_v1.py"
PROBE = ROOT / "scripts" / "probe_layer1_only_brier_bench_resolvers_v1.py"
SYNC = ROOT / "scripts" / "sync_layer1_only_brier_bench_resolutions_v1.py"
EVAL = ROOT / "scripts" / "layer1_only_brier_bench_poc_v1.py"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Register/sync dry-run; probe dry-run unless --live.")
    ap.add_argument("--live", action="store_true", help="Network probes (holdout-safe before deadlines).")
    ap.add_argument("--allow-simulation", action="store_true", help="Pass through to eval for [HYPO] math smoke.")
    ap.add_argument("--skip-register", action="store_true")
    ns = ap.parse_args()

    steps: list[dict[str, object]] = []

    if not ns.skip_register:
        reg_cmd = [sys.executable, str(REGISTER)]
        if ns.dry_run:
            reg_cmd.append("--dry-run")
        reg = _run(reg_cmd)
        steps.append({"step": "register", "exit_code": reg.returncode})
        if reg.returncode != 0:
            print(reg.stderr or reg.stdout, file=sys.stderr)
            return reg.returncode

    probe_cmd = [sys.executable, str(PROBE)]
    if ns.live:
        probe_cmd.append("--live")
    probe = _run(probe_cmd)
    steps.append({"step": "probe", "exit_code": probe.returncode})
    if probe.returncode != 0:
        print(probe.stderr or probe.stdout, file=sys.stderr)
        return probe.returncode

    sync_cmd = [sys.executable, str(SYNC)]
    if ns.dry_run:
        sync_cmd.append("--dry-run")
    sync = _run(sync_cmd)
    steps.append({"step": "sync_resolutions", "exit_code": sync.returncode})
    if sync.returncode != 0:
        print(sync.stderr or sync.stdout, file=sys.stderr)
        return sync.returncode

    eval_cmd = [sys.executable, str(EVAL)]
    if ns.allow_simulation:
        eval_cmd.append("--allow-simulation")
    ev = _run(eval_cmd)
    steps.append({"step": "evaluate", "exit_code": ev.returncode})
    if ev.returncode != 0:
        print(ev.stderr or ev.stdout, file=sys.stderr)
        return ev.returncode

    summary = {
        "schema": "layer1_only_brier_bench_chain_v1",
        "track_wall": "B",
        "auto_bridge_to_a": False,
        "dry_run": ns.dry_run,
        "live_probe": ns.live,
        "steps": steps,
    }
    out = ROOT / "reports" / "layer1_only_brier_bench_chain_v1_latest.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"chain summary written to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
