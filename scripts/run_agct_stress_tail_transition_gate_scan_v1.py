#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=False, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"step_failed returncode={r.returncode}")


def _stage_csv_with_header_check(src: Path, dst: Path, required: tuple[str, ...]) -> Path:
    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = tuple(reader.fieldnames or ())
        missing = [c for c in required if c not in fields]
        if missing:
            raise SystemExit(f"{src} missing required columns: {missing} (found={list(fields)})")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


def _read_json_safe(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        raise RuntimeError(f"empty_json:{path}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        dec = json.JSONDecoder()
        obj, _idx = dec.raw_decode(raw)
        if not isinstance(obj, dict):
            raise RuntimeError(f"invalid_json_object:{path}")
        return obj


def _normalize_row(row: dict[str, float]) -> dict[str, float]:
    s = sum(float(row[a]) for a in AXES)
    if s <= 0:
        return {a: 0.25 for a in AXES}
    return {a: float(row[a]) / s for a in AXES}


def _mutate_weights(base: dict[str, dict[str, float]], rng: random.Random, sigma: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        row = {}
        for a in AXES:
            v = float(base[b][a]) + rng.gauss(0.0, sigma)
            row[a] = max(1e-9, v)
        out[b] = _normalize_row(row)
    return out


def _parse_sigmas(s: str) -> list[float]:
    out = []
    for p in s.split(","):
        p = p.strip()
        if p:
            out.append(float(p))
    if not out:
        raise ValueError("No sigma values provided.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Stress-tail transition scan with GO_BTRACK retention checks.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--sigmas", type=str, default="0.025,0.0275,0.03,0.0325,0.035")
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--cohort-csv", type=Path, default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument("--genotype-csv", type=Path, default=root / "tmp" / "bio_genotype_long_v1.csv")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_stress_tail_transition_gate_scan_v1_latest.json",
    )
    ns = ap.parse_args()

    sigmas = _parse_sigmas(ns.sigmas)
    base_w = _read_json_safe(ns.base_weights_json)
    contrib_script = root / "scripts" / "run_agct_sasang_formula_contribution_report_v1.py"
    daily_script = root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py"
    work = root / "tmp" / "agct_stress_transition_scan_v1"
    work.mkdir(parents=True, exist_ok=True)
    run_tag = f"seed_{ns.seed}_{int(time.time())}"
    run_work = work / run_tag
    run_work.mkdir(parents=True, exist_ok=True)
    # Snapshot inputs once to prevent mid-run schema/file churn from concurrent jobs.
    staged_cohort = _stage_csv_with_header_check(
        ns.cohort_csv,
        run_work / "cohort_snapshot.csv",
        ("sample_id", "risk_score"),
    )
    staged_genotype = _stage_csv_with_header_check(
        ns.genotype_csv,
        run_work / "genotype_snapshot.csv",
        ("sample_id", "genotype"),
    )

    rows = []
    for si, sigma in enumerate(sigmas):
        t_sigma = time.perf_counter()
        print(f"[STEP] sigma={sigma} ({si+1}/{len(sigmas)})", flush=True)
        top_counts: dict[str, int] = {}
        go_count = 0
        for t in range(ns.trials):
            trial_seed = ns.seed + si * 1000 + t
            if t == 0 or (t + 1) % 10 == 0 or t == ns.trials - 1:
                print(
                    f"[PROGRESS] sigma={sigma} trial={t+1}/{ns.trials} seed={trial_seed}",
                    flush=True,
                )
            rng = random.Random(trial_seed)
            w = _mutate_weights(base_w, rng, sigma)
            w_path = work / f"sigma_{str(sigma).replace('.','_')}_trial_{t:03d}_weights.json"
            c_path = work / f"sigma_{str(sigma).replace('.','_')}_trial_{t:03d}_contrib.json"
            d_path = work / f"sigma_{str(sigma).replace('.','_')}_trial_{t:03d}_daily.json"
            w_path.write_text(json.dumps(w, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            _run(
                [
                    sys.executable,
                    str(contrib_script),
                    "--cohort-csv",
                    str(staged_cohort),
                    "--genotype-csv",
                    str(staged_genotype),
                    "--weights-json",
                    str(w_path),
                    "--output-json",
                    str(c_path),
                ]
            )
            c = _read_json_safe(c_path)
            stress_ranking = ((c.get("segment_reports", {}).get("stress_tail", {}) or {}).get("ranking_summary", []) or [])
            top = stress_ranking[0]["component"] if stress_ranking else "unknown"
            top_counts[top] = top_counts.get(top, 0) + 1

            _run(
                [
                    sys.executable,
                    str(daily_script),
                    "--active-weights-json",
                    str(w_path),
                    "--cohort-csv",
                    str(staged_cohort),
                    "--genotype-csv",
                    str(staged_genotype),
                    "--seed",
                    str(trial_seed),
                    "--output-json",
                    str(d_path),
                ]
            )
            d = _read_json_safe(d_path)
            if d.get("decision") == "GO_BTRACK":
                go_count += 1

        dominant_component = max(top_counts.items(), key=lambda kv: kv[1])[0]
        dominant_share = top_counts[dominant_component] / ns.trials
        row = {
            "sigma": sigma,
            "stress_tail_top_component_frequency": top_counts,
            "stress_tail_dominant_component": dominant_component,
            "stress_tail_dominant_share": dominant_share,
            "go_rate": go_count / ns.trials,
            "transition_intensity": 1.0 - dominant_share,
        }
        rows.append(row)
        dt_sigma = time.perf_counter() - t_sigma
        print(
            f"[DONE] sigma={sigma} go_rate={row['go_rate']:.3f} transition_intensity={row['transition_intensity']:.3f} elapsed_sec={dt_sigma:.1f}",
            flush=True,
        )

    baseline_dom = rows[0]["stress_tail_dominant_component"] if rows else None
    first_flip_sigma = None
    for r in rows:
        if r["stress_tail_dominant_component"] != baseline_dom:
            first_flip_sigma = r["sigma"]
            break

    best_row = max(rows, key=lambda r: (r["go_rate"], r["transition_intensity"])) if rows else None
    payload = {
        "schema": "agct_stress_tail_transition_gate_scan_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "sigmas": sigmas,
            "trials": ns.trials,
            "seed": ns.seed,
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "cohort_csv": str(staged_cohort.resolve()),
            "genotype_csv": str(staged_genotype.resolve()),
            "run_work_dir": str(run_work.resolve()),
        },
        "rows": rows,
        "summary": {
            "baseline_dominant_component": baseline_dom,
            "first_dominant_flip_sigma": first_flip_sigma,
            "best_sigma_by_go_then_transition": (best_row or {}).get("sigma"),
        },
        "notes": [
            "Transition intensity = 1 - dominant share in stress_tail.",
            "Use GO rate + transition intensity jointly; B-track diagnostics only.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} sigmas={len(sigmas)} trials={ns.trials}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
