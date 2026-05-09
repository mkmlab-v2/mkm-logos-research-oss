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


def _daily_eval(root: Path, weights_json: Path, active_path: Path) -> dict:
    backup = active_path.with_suffix(".backup_sigma_grid.json")
    shutil.copy2(active_path, backup)
    try:
        shutil.copy2(weights_json, active_path)
        _run([sys.executable, str(root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py")], root)
        d = json.loads((root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json").read_text(encoding="utf-8"))
        return {
            "decision": d["decision"],
            "checks": d["checks"],
            "metrics": d["metrics"],
        }
    finally:
        shutil.copy2(backup, active_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Joint-retune sigma grid + daily-chain gate scan.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--iterations", type=int, default=128)
    ap.add_argument("--sigmas", type=str, default="0.05,0.08,0.12")
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_joint_retune_sigma_grid_v1_latest.json")
    ns = ap.parse_args()

    joint_script = root / "scripts" / "run_agct_joint_retune_robust_external_v1.py"
    active_path = root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json"

    rows = []
    best = None
    for idx, sigma_s in enumerate([s.strip() for s in ns.sigmas.split(",") if s.strip()]):
        sigma = float(sigma_s)
        out = root / "reports" / f"agct_joint_retune_sigma_{sigma_s.replace('.','_')}.json"
        best_weights = root / "tmp" / f"agct_sasang_axis_weights_joint_candidate_sigma_{sigma_s.replace('.','_')}.json"
        _run(
            [
                sys.executable,
                str(joint_script),
                "--base-weights-json",
                str(ns.base_weights_json),
                "--iterations",
                str(ns.iterations),
                "--sigma",
                str(sigma),
                "--seed",
                str(ns.seed + idx * 1000),
                "--best-weights-out-json",
                str(best_weights),
                "--output-json",
                str(out),
            ],
            root,
        )
        retune = json.loads(out.read_text(encoding="utf-8"))
        daily = _daily_eval(root, best_weights, active_path)
        row = {
            "sigma": sigma,
            "retune_report": str(out.resolve()),
            "best_weights_json": str(best_weights.resolve()),
            "retune_best_metrics": retune["summary"]["best_metrics"],
            "daily_decision": daily["decision"],
            "daily_checks": daily["checks"],
            "daily_metrics": daily["metrics"],
            "daily_all_ok": all(daily["checks"].values()),
        }
        rows.append(row)
        if best is None or float(row["daily_metrics"]["external_risk_corr_observed"]) > float(best["daily_metrics"]["external_risk_corr_observed"]):
            best = row

    payload = {
        "schema": "agct_joint_retune_sigma_grid_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "iterations": ns.iterations,
            "sigmas": ns.sigmas,
        },
        "summary": {
            "n_runs": len(rows),
            "any_daily_all_ok": any(r["daily_all_ok"] for r in rows),
            "best_by_daily_external_corr": best,
        },
        "runs": rows,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} any_daily_all_ok={payload['summary']['any_daily_all_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
