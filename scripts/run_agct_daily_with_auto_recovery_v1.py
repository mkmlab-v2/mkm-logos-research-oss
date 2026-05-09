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


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _score_daily(d: dict) -> float:
    m = d["metrics"]
    checks = d["checks"]
    # prioritize gate pass count, then external corr, then robustness
    pass_count = sum(1 for v in checks.values() if v is True)
    return float(pass_count) + float(m.get("external_risk_corr_observed", 0.0)) + 0.5 * float(m.get("robustness_observed", 0.0))


def _evaluate_weight_on_seed_window(root: Path, daily_script: Path, daily_report: Path, weight_path: Path, active_weights: Path, center_seed: int, radius: int) -> dict:
    backup = active_weights.with_suffix(".backup_micro_sweep.json")
    shutil.copy2(active_weights, backup)
    try:
        shutil.copy2(weight_path, active_weights)
        rows = []
        for s in range(center_seed - radius, center_seed + radius + 1):
            _run([sys.executable, str(daily_script), "--seed", str(s)], root)
            d = _read_json(daily_report)
            rows.append(
                {
                    "seed": s,
                    "decision": d["decision"],
                    "checks": d["checks"],
                    "metrics": d["metrics"],
                    "score": _score_daily(d),
                }
            )
        go_count = sum(1 for r in rows if r["decision"] == "GO_BTRACK")
        avg_score = sum(r["score"] for r in rows) / len(rows) if rows else 0.0
        return {"rows": rows, "go_count": go_count, "avg_score": avg_score}
    finally:
        shutil.copy2(backup, active_weights)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run daily chain, then auto-recover when REVIEW_REQUIRED.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--retune-iterations", type=int, default=40)
    ap.add_argument("--retune-sigma", type=float, default=0.06)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--micro-sweep-radius", type=int, default=2)
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_daily_auto_recovery_v1_latest.json")
    ns = ap.parse_args()

    daily_script = root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py"
    recover_script = root / "scripts" / "run_agct_extcorr_constrained_retune_v1.py"
    daily_report = root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json"
    active_weights = root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json"
    recover_weights = root / "tmp" / "agct_sasang_axis_weights_extcorr_candidate_v1.json"
    recover_report = root / "reports" / "agct_extcorr_constrained_retune_v1_latest.json"
    shadow_weights = root / "tmp" / "agct_sasang_axis_weights_active_robust_candidate_v1.json"
    active_backup = active_weights.with_suffix(".backup_auto_recovery_v2.json")

    shutil.copy2(active_weights, active_backup)
    _run([sys.executable, str(daily_script), "--seed", str(ns.seed)], root)
    before = _read_json(daily_report)
    recovered = False
    retry_logs: list[dict] = []
    best_daily = before
    best_source = "before"
    best_micro = {
        "go_count": 1 if before["decision"] == "GO_BTRACK" else 0,
        "avg_score": _score_daily(before),
        "rows": [{"seed": ns.seed, "decision": before["decision"], "checks": before["checks"], "metrics": before["metrics"], "score": _score_daily(before)}],
    }

    if before["decision"] != "GO_BTRACK":
        # multiple constrained-retune attempts, keep best candidate by score
        for k in range(ns.max_retries):
            _run(
                [
                    sys.executable,
                    str(recover_script),
                    "--iterations",
                    str(ns.retune_iterations),
                    "--sigma",
                    str(ns.retune_sigma),
                    "--seed",
                    str(ns.seed + k * 100),
                ],
                root,
            )
            if recover_weights.exists():
                cand = root / "tmp" / f"agct_sasang_axis_weights_extcorr_candidate_retry{k:02d}.json"
                shutil.copy2(recover_weights, cand)
                micro = _evaluate_weight_on_seed_window(
                    root,
                    daily_script,
                    daily_report,
                    cand,
                    active_weights,
                    ns.seed,
                    ns.micro_sweep_radius,
                )
                center_row = next((r for r in micro["rows"] if r["seed"] == ns.seed), micro["rows"][0])
                retry_logs.append(
                    {
                        "retry": k + 1,
                        "candidate_weights": str(cand.resolve()),
                        "decision": center_row["decision"],
                        "checks": center_row["checks"],
                        "metrics": center_row["metrics"],
                        "score": center_row["score"],
                        "micro_sweep": {
                            "radius": ns.micro_sweep_radius,
                            "go_count": micro["go_count"],
                            "avg_score": micro["avg_score"],
                        },
                    }
                )
                if (micro["go_count"], micro["avg_score"]) > (best_micro["go_count"], best_micro["avg_score"]):
                    best_daily = {"decision": center_row["decision"], "checks": center_row["checks"], "metrics": center_row["metrics"]}
                    best_source = str(cand.resolve())
                    best_micro = micro
                if center_row["decision"] == "GO_BTRACK":
                    recovered = True
                    break

        # if still not GO, try shadow fallback
        if not recovered and shadow_weights.exists():
            micro = _evaluate_weight_on_seed_window(
                root,
                daily_script,
                daily_report,
                shadow_weights,
                active_weights,
                ns.seed,
                ns.micro_sweep_radius,
            )
            center_row = next((r for r in micro["rows"] if r["seed"] == ns.seed), micro["rows"][0])
            retry_logs.append(
                {
                    "retry": "shadow_fallback",
                    "candidate_weights": str(shadow_weights.resolve()),
                    "decision": center_row["decision"],
                    "checks": center_row["checks"],
                    "metrics": center_row["metrics"],
                    "score": center_row["score"],
                    "micro_sweep": {
                        "radius": ns.micro_sweep_radius,
                        "go_count": micro["go_count"],
                        "avg_score": micro["avg_score"],
                    },
                }
            )
            if (micro["go_count"], micro["avg_score"]) > (best_micro["go_count"], best_micro["avg_score"]):
                best_daily = {"decision": center_row["decision"], "checks": center_row["checks"], "metrics": center_row["metrics"]}
                best_source = str(shadow_weights.resolve())
                best_micro = micro
            if center_row["decision"] == "GO_BTRACK":
                recovered = True

        # finalize with best candidate found
        if best_source != "before":
            if best_source == str(shadow_weights.resolve()):
                shutil.copy2(shadow_weights, active_weights)
            else:
                shutil.copy2(Path(best_source), active_weights)
            _run([sys.executable, str(daily_script), "--seed", str(ns.seed)], root)

    after = _read_json(daily_report)
    payload = {
        "schema": "agct_daily_auto_recovery_v1",
        "generated_at_utc": _utc_now(),
        "seed": ns.seed,
        "before": {"decision": before["decision"], "checks": before["checks"], "metrics": before["metrics"]},
        "auto_recovery_triggered": before["decision"] != "GO_BTRACK",
        "recovery_executed": recovered,
        "max_retries": ns.max_retries,
        "micro_sweep_radius": ns.micro_sweep_radius,
        "best_candidate_source": best_source,
        "best_candidate_micro_sweep": {
            "go_count": best_micro["go_count"],
            "avg_score": best_micro["avg_score"],
        },
        "retry_logs": retry_logs,
        "after": {"decision": after["decision"], "checks": after["checks"], "metrics": after["metrics"]},
        "artifacts": {
            "daily_report": str(daily_report.resolve()),
            "recovery_report": str(recover_report.resolve()) if recover_report.exists() else None,
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} "
        f"before={before['decision']} after={after['decision']} recovery={recovered}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
