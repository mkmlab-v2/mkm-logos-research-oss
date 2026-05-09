#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.86, K:0.68, M:0.45}
# Balance: 89
# Purpose: Validate AGCT composition projection profile stability via bootstrap resampling.
# Keywords: agct, sasang, composition, stability, bootstrap, btrack

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from json import JSONDecodeError, JSONDecoder
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return var**0.5


def _write_subset_csv(src: Path, dst: Path, sample_col: str, keep_ids: set[str]) -> None:
    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = [r for r in reader if str(r.get(sample_col) or "").strip() in keep_ids]
    with dst.open("w", encoding="utf-8", newline="") as fw:
        writer = csv.DictWriter(fw, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_first_json_object(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except JSONDecodeError:
        # Some environments can leave concatenated JSON blobs in temp files.
        # For stability sweeps we only need the first valid object.
        decoder = JSONDecoder()
        obj, _ = decoder.raw_decode(raw.lstrip())
        if not isinstance(obj, dict):
            raise
        return obj


def _collect_sample_ids(path: Path, sample_col: str) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sorted({str(r.get(sample_col) or "").strip() for r in reader if str(r.get(sample_col) or "").strip()})


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap stability check for AGCT composition profile.")
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--axis-weights-json", type=Path, required=True)
    ap.add_argument("--projection-script", type=Path, default=Path("scripts/run_agct_sasang_composition_projection_v1.py"))
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--sample-ratio", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--work-dir", type=Path, default=Path("tmp/agct_profile_stability_v1"))
    ap.add_argument("--output-json", type=Path, default=Path("reports/agct_sasang_composition_profile_stability_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    ns.work_dir.mkdir(parents=True, exist_ok=True)

    all_ids = _collect_sample_ids(ns.cohort_csv, ns.sample_col)
    if not all_ids:
        raise SystemExit("No sample ids in cohort csv.")
    k = max(4, int(round(len(all_ids) * ns.sample_ratio)))

    scores: list[float] = []
    gaps: list[float] = []
    risk_sums: list[float] = []
    round_rows: list[dict] = []

    for i in range(ns.rounds):
        picked = set(rng.sample(all_ids, min(k, len(all_ids))))
        cohort_sub = ns.work_dir / f"round_{i:03d}_cohort.csv"
        geno_sub = ns.work_dir / f"round_{i:03d}_geno.csv"
        out_json = ns.work_dir / f"round_{i:03d}_projection.json"

        _write_subset_csv(ns.cohort_csv, cohort_sub, ns.sample_col, picked)
        _write_subset_csv(ns.genotype_csv, geno_sub, ns.sample_col, picked)

        cmd = [
            sys.executable,
            str(ns.projection_script),
            "--genotype-csv",
            str(geno_sub),
            "--cohort-csv",
            str(cohort_sub),
            "--axis-weights-json",
            str(ns.axis_weights_json),
            "--output-json",
            str(out_json),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"projection round {i} failed: {res.stderr or res.stdout}")

        obj = _read_first_json_object(out_json)
        axis_summary = obj["summary"]["axis_summary"]
        risk = obj["risk_axis_correlations"]
        gap = max(v["mean_projection"] for v in axis_summary.values()) - min(v["mean_projection"] for v in axis_summary.values())
        risk_sum = sum(abs((risk.get(ax, {}) or {}).get("pearson_corr_with_risk") or 0.0) for ax in ("TY", "SY", "TE", "SE"))
        score = float(risk_sum - gap)

        scores.append(score)
        gaps.append(gap)
        risk_sums.append(risk_sum)
        round_rows.append(
            {
                "round": i,
                "n_samples": len(picked),
                "objective_score": score,
                "axis_balance_gap": gap,
                "risk_signal_score": risk_sum,
            }
        )

    payload = {
        "schema": "agct_sasang_composition_profile_stability_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {"research_only": True, "non_gating": True, "human_review_required": True},
        "inputs": {
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "axis_weights_json": str(ns.axis_weights_json.resolve()),
            "rounds": int(ns.rounds),
            "sample_ratio": float(ns.sample_ratio),
            "seed": int(ns.seed),
        },
        "summary": {
            "objective_score_mean": _mean(scores),
            "objective_score_std": _std(scores),
            "objective_score_min": min(scores) if scores else 0.0,
            "objective_score_max": max(scores) if scores else 0.0,
            "axis_balance_gap_mean": _mean(gaps),
            "risk_signal_score_mean": _mean(risk_sums),
            "stability_pass": (_std(scores) <= 0.25),
        },
        "rounds": round_rows,
        "notes": [
            "Bootstrap stability is exploratory only.",
            "Do not use as clinical evidence or production trigger.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} score_mean={payload['summary']['objective_score_mean']:.6f} "
        f"score_std={payload['summary']['objective_score_std']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
