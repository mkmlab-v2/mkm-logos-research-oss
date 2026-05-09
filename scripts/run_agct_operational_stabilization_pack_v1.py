#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> None:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build operational stabilization pack (snapshot + 10-run watch).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--start-seed", type=int, default=20260505)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_operational_stabilization_pack_v1_latest.json")
    ns = ap.parse_args()

    daily_script = root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py"
    snapshot_dir = root / "reports" / "agct_snapshot_pack_v1"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 1) snapshot lock
    active_weights = root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json"
    daily_latest = root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json"
    extcorr_latest = root / "reports" / "agct_extcorr_constrained_retune_v1_latest.json"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    weights_snap = snapshot_dir / f"weights_active_{stamp}.json"
    daily_snap = snapshot_dir / f"daily_chain_{stamp}.json"
    extcorr_snap = snapshot_dir / f"extcorr_retune_{stamp}.json"
    shutil.copy2(active_weights, weights_snap)
    shutil.copy2(daily_latest, daily_snap)
    if extcorr_latest.exists():
        shutil.copy2(extcorr_latest, extcorr_snap)

    # 2) 10-run watch
    runs = []
    for i in range(ns.runs):
        seed = ns.start_seed + i
        _run([sys.executable, str(daily_script), "--seed", str(seed)], root)
        d = json.loads(daily_latest.read_text(encoding="utf-8"))
        runs.append({"seed": seed, "decision": d["decision"], "checks": d["checks"], "metrics": d["metrics"]})

    go_count = sum(1 for r in runs if r["decision"] == "GO_BTRACK")
    payload = {
        "schema": "agct_operational_stabilization_pack_v1",
        "generated_at_utc": _utc_now(),
        "snapshot": {
            "weights_snapshot": str(weights_snap.resolve()),
            "daily_snapshot": str(daily_snap.resolve()),
            "extcorr_snapshot": str(extcorr_snap.resolve()) if extcorr_latest.exists() else None,
        },
        "watch10": {
            "runs": runs,
            "summary": {
                "n_runs": ns.runs,
                "go_count": go_count,
                "go_ratio": go_count / ns.runs if ns.runs else 0.0,
                "all_go": go_count == ns.runs,
            },
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} go_ratio={payload['watch10']['summary']['go_ratio']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
