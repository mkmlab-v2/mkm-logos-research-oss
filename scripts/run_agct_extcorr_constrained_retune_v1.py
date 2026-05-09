#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> None:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _normalize_row(row: dict[str, float]) -> dict[str, float]:
    for k in AXES:
        row[k] = max(0.0, float(row.get(k, 0.0)))
    s = sum(row.values())
    if s <= 0:
        return {k: 0.25 for k in AXES}
    return {k: row[k] / s for k in AXES}


def _mutate(w: dict[str, dict[str, float]], rng: random.Random, sigma: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        row = {ax: float(w[b][ax]) + rng.uniform(-sigma, sigma) for ax in AXES}
        out[b] = _normalize_row(row)
    return out


def _daily_eval(root: Path, weights_json: Path, seed: int) -> dict:
    active = root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json"
    backup = active.with_suffix(".backup_extcorr_retune.json")
    shutil.copy2(active, backup)
    try:
        shutil.copy2(weights_json, active)
        _run([sys.executable, str(root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py"), "--seed", str(seed)], root)
        return json.loads((root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json").read_text(encoding="utf-8"))
    finally:
        shutil.copy2(backup, active)


def main() -> int:
    ap = argparse.ArgumentParser(description="Constrained retune for external risk correlation.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--iterations", type=int, default=80)
    ap.add_argument("--sigma", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--constrain-robustness-min", type=float, default=0.13)
    ap.add_argument("--best-weights-out-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_extcorr_candidate_v1.json")
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_extcorr_constrained_retune_v1_latest.json")
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    base = json.loads(ns.base_weights_json.read_text(encoding="utf-8"))
    work = root / "tmp" / "agct_extcorr_retune_v1"
    work.mkdir(parents=True, exist_ok=True)

    inc = base
    inc_path = work / "incumbent_weights.json"
    inc_path.write_text(json.dumps(inc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d0 = _daily_eval(root, inc_path, ns.seed)
    m0 = d0["metrics"]
    inc_score = float(m0["external_risk_corr_observed"]) if float(m0["robustness_observed"]) >= ns.constrain_robustness_min else -1.0
    inc_daily = d0

    trials = []
    for i in range(ns.iterations):
        cand = _mutate(inc, rng, ns.sigma)
        cand_path = work / f"cand_{i:03d}_weights.json"
        cand_path.write_text(json.dumps(cand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        d = _daily_eval(root, cand_path, ns.seed + i + 1)
        m = d["metrics"]
        robust = float(m["robustness_observed"])
        ext_corr = float(m["external_risk_corr_observed"])
        feasible = robust >= ns.constrain_robustness_min
        score = ext_corr if feasible else -1.0
        accepted = score > inc_score
        if accepted:
            inc = cand
            inc_score = score
            inc_daily = d
            inc_path.write_text(json.dumps(inc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        trials.append(
            {
                "iter": i,
                "accepted": accepted,
                "feasible": feasible,
                "score_external_corr": score,
                "metrics": m,
                "checks": d["checks"],
                "decision": d["decision"],
            }
        )

    ns.best_weights_out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.best_weights_out_json.write_text(json.dumps(inc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {
        "schema": "agct_extcorr_constrained_retune_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "iterations": ns.iterations,
            "sigma": ns.sigma,
            "constrain_robustness_min": ns.constrain_robustness_min,
        },
        "summary": {
            "best_external_risk_corr_under_constraint": inc_score,
            "best_daily_decision": inc_daily["decision"],
            "best_daily_checks": inc_daily["checks"],
            "best_daily_metrics": inc_daily["metrics"],
            "accepted_moves": sum(1 for t in trials if t["accepted"]),
        },
        "outputs": {
            "best_weights_json": str(ns.best_weights_out_json.resolve()),
            "work_dir": str(work.resolve()),
        },
        "trials": trials,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} "
        f"best_ext_corr={inc_score:.4f} decision={inc_daily['decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
