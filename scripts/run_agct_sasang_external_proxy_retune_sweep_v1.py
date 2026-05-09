#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mutate(base: dict[str, dict[str, float]], rng: random.Random, jitter: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        out[b] = {}
        for a in AXES:
            out[b][a] = max(0.01, round(float(base[b][a]) + rng.uniform(-jitter, jitter), 6))
    return out


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Retune active AGCT weights against external proxy + internal guard.")
    ap.add_argument("--active-weights-json", type=Path, required=True)
    ap.add_argument("--external-eval-script", type=Path, default=Path("scripts/run_agct_sasang_external_blind_proxy_eval_v1.py"))
    ap.add_argument("--internal-projection-script", type=Path, default=Path("scripts/run_agct_sasang_composition_projection_v1.py"))
    ap.add_argument("--internal-genotype-csv", type=Path, required=True)
    ap.add_argument("--internal-cohort-csv", type=Path, required=True)
    ap.add_argument("--external-n-samples", type=int, default=1200)
    ap.add_argument("--candidates", type=int, default=40)
    ap.add_argument("--jitter", type=float, default=0.08)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--max-internal-objective-drop", type=float, default=0.15)
    ap.add_argument("--work-dir", type=Path, default=Path("tmp/agct_external_retune_sweep_v1"))
    ap.add_argument("--output-json", type=Path, default=Path("reports/agct_sasang_external_proxy_retune_sweep_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    ns.work_dir.mkdir(parents=True, exist_ok=True)
    base = json.loads(ns.active_weights_json.read_text(encoding="utf-8"))

    # Baseline internal objective
    baseline_internal_json = ns.work_dir / "baseline_internal_projection.json"
    _run(
        [
            sys.executable,
            str(ns.internal_projection_script),
            "--genotype-csv",
            str(ns.internal_genotype_csv),
            "--cohort-csv",
            str(ns.internal_cohort_csv),
            "--axis-weights-json",
            str(ns.active_weights_json),
            "--output-json",
            str(baseline_internal_json),
        ]
    )
    bi = json.loads(baseline_internal_json.read_text(encoding="utf-8"))
    axis_summary = bi["summary"]["axis_summary"]
    risk = bi["risk_axis_correlations"]
    baseline_internal_obj = sum(abs((risk.get(a, {}) or {}).get("pearson_corr_with_risk") or 0.0) for a in AXES)
    baseline_internal_obj -= max(v["mean_projection"] for v in axis_summary.values()) - min(
        v["mean_projection"] for v in axis_summary.values()
    )

    rows: list[dict] = []
    for i in range(max(1, ns.candidates)):
        pid = f"cand_{i:03d}" if i else "baseline"
        weights = base if i == 0 else _mutate(base, rng, ns.jitter)
        w_json = ns.work_dir / f"{pid}_weights.json"
        w_json.write_text(json.dumps(weights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        ext_json = ns.work_dir / f"{pid}_external_eval.json"
        _run(
            [
                sys.executable,
                str(ns.external_eval_script),
                "--n-samples",
                str(ns.external_n_samples),
                "--seed",
                str(ns.seed + i),
                "--active-weights-json",
                str(w_json),
                "--output-json",
                str(ext_json),
            ]
        )
        ex = json.loads(ext_json.read_text(encoding="utf-8"))
        ext_acc = float(ex["summary"]["top_axis_accuracy_vs_proxy_label"])
        ext_corr = float(ex["summary"]["predicted_risk_corr_with_proxy_risk"] or 0.0)

        in_json = ns.work_dir / f"{pid}_internal_projection.json"
        _run(
            [
                sys.executable,
                str(ns.internal_projection_script),
                "--genotype-csv",
                str(ns.internal_genotype_csv),
                "--cohort-csv",
                str(ns.internal_cohort_csv),
                "--axis-weights-json",
                str(w_json),
                "--output-json",
                str(in_json),
            ]
        )
        inn = json.loads(in_json.read_text(encoding="utf-8"))
        s = inn["summary"]["axis_summary"]
        r = inn["risk_axis_correlations"]
        internal_obj = sum(abs((r.get(a, {}) or {}).get("pearson_corr_with_risk") or 0.0) for a in AXES)
        internal_obj -= max(v["mean_projection"] for v in s.values()) - min(v["mean_projection"] for v in s.values())

        drop = baseline_internal_obj - internal_obj
        pass_guard = drop <= float(ns.max_internal_objective_drop)
        composite = ext_acc + (0.35 * ext_corr) + (0.10 * internal_obj)
        rows.append(
            {
                "profile_id": pid,
                "weights_json": str(w_json.resolve()),
                "external_accuracy": ext_acc,
                "external_risk_corr": ext_corr,
                "internal_objective": internal_obj,
                "internal_drop_vs_baseline": drop,
                "pass_internal_guard": pass_guard,
                "composite_score": composite,
            }
        )

    eligible = [r for r in rows if r["pass_internal_guard"]]
    ranked = sorted(eligible if eligible else rows, key=lambda x: x["composite_score"], reverse=True)
    best = ranked[0]

    payload = {
        "schema": "agct_sasang_external_proxy_retune_sweep_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {"research_only": True, "non_gating": True, "human_review_required": True},
        "inputs": {
            "active_weights_json": str(ns.active_weights_json.resolve()),
            "candidates": int(ns.candidates),
            "jitter": float(ns.jitter),
            "seed": int(ns.seed),
            "external_n_samples": int(ns.external_n_samples),
            "max_internal_objective_drop": float(ns.max_internal_objective_drop),
        },
        "baseline_internal_objective": baseline_internal_obj,
        "eligible_count": len(eligible),
        "best_profile": best,
        "top_profiles": ranked[:10],
        "notes": [
            "External proxy retune is exploratory only.",
            "Do not promote to A-track without independent real cohort blind test.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} best={best['profile_id']} score={best['composite_score']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
