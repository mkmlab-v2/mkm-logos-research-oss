# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.9, K:0.8, M:0.5}
# Balance: 90
# Purpose: Run blind replay across multiple dataset configs and compare scores.
# Keywords: blind-replay, dataset-grid, ablation, profile-sweep, exploratory_only
#!/usr/bin/env python3
"""Run blind replay dataset grid and profile sweep comparison."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLIND_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "blind_replay"
GRID_REPORT = BLIND_DIR / "blind_replay_dataset_grid_latest.json"
RANKING_FILE = BLIND_DIR / "blind_replay_profile_ranking_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = sum(values) / len(values)
    v = sum((x - m) ** 2 for x in values) / len(values)
    return m, math.sqrt(v)


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _slug(s: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return text or "dataset"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run blind replay dataset grid + profile sweep.")
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--sample-size", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42, help="Legacy single-seed mode (used when --seeds omitted).")
    ap.add_argument("--seeds", default="", help="Comma-separated seeds (e.g. 41,42,43)")
    ap.add_argument("--profiles", default="A,B,C", help="Comma-separated profiles for sweep (e.g. A,B,C or A)")
    ap.add_argument(
        "--dataset-id",
        default="",
        help="Dataset namespace for output filenames; defaults to input CSV stem.",
    )
    ap.add_argument(
        "--min-matched",
        type=int,
        default=20,
        help="Minimum matched sample count required for ranking eligibility (default: 20).",
    )
    ap.add_argument(
        "--dense-grid",
        action="store_true",
        help="Include denser stride configs to increase sample diversity.",
    )
    ap.add_argument("--out", type=Path, default=GRID_REPORT)
    args = ap.parse_args()

    # (window, horizon, stride)
    configs = [
        (30, 5, 3),
        (45, 10, 5),
        (60, 10, 5),
    ]
    if args.dense_grid:
        configs.extend(
            [
                (30, 5, 1),
                (45, 10, 2),
                (60, 10, 2),
            ]
        )
    if str(args.seeds).strip():
        seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    else:
        seeds = [int(args.seed)]
    dataset_id = _slug(str(args.dataset_id).strip()) if str(args.dataset_id).strip() else _slug(args.input_csv.stem)

    results: list[dict[str, Any]] = []
    for i, (w, h, s) in enumerate(configs, start=1):
        tag = f"cfg{i}_w{w}_h{h}_s{s}"
        seed_runs: list[dict[str, Any]] = []
        for seed in seeds:
            seed_tag = f"{dataset_id}_{tag}_seed{seed}"
            public = BLIND_DIR / f"blind_replay_public_{seed_tag}.jsonl"
            key = BLIND_DIR / f"blind_replay_answer_key_{seed_tag}.jsonl"

            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "blind_historical_replay.py"),
                    "--input-csv",
                    str(args.input_csv),
                    "--window-bars",
                    str(w),
                    "--horizon-bars",
                    str(h),
                    "--stride",
                    str(s),
                    "--sample-size",
                    str(args.sample_size),
                    "--seed",
                    str(seed),
                ]
            )

            manifest = _read_json(BLIND_DIR / "blind_replay_manifest_latest.json")
            latest_public = Path(str(manifest.get("public_dataset") or ""))
            latest_key = Path(str(manifest.get("private_answer_key") or ""))
            if not latest_public.is_file() or not latest_key.is_file():
                raise SystemExit("blind_historical_replay did not produce expected output files")
            public.write_text(latest_public.read_text(encoding="utf-8"), encoding="utf-8")
            key.write_text(latest_key.read_text(encoding="utf-8"), encoding="utf-8")

            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_blind_replay_profile_sweep.py"),
                    "--public-dataset",
                    str(public),
                    "--answer-key",
                    str(key),
                    "--profiles",
                    str(args.profiles),
                ]
            )
            ranking = _read_json(RANKING_FILE)
            best = ranking.get("best_profile") if isinstance(ranking.get("best_profile"), dict) else {}
            profiles = ranking.get("profiles") if isinstance(ranking.get("profiles"), list) else []
            avg_hit = sum(float(p.get("hit_rate") or 0.0) for p in profiles) / max(1, len(profiles))
            avg_bal = sum(float(p.get("balanced_accuracy") or 0.0) for p in profiles) / max(1, len(profiles))
            seed_runs.append(
                {
                    "seed": seed,
                    "public_dataset": str(public.resolve()),
                    "answer_key": str(key.resolve()),
                    "best_profile": best,
                    "avg_hit_rate_profiles": round(avg_hit, 6),
                    "avg_balanced_accuracy_profiles": round(avg_bal, 6),
                }
            )

        best_hit_vals = [float((x.get("best_profile") or {}).get("hit_rate") or 0.0) for x in seed_runs]
        best_bal_vals = [float((x.get("best_profile") or {}).get("balanced_accuracy") or 0.0) for x in seed_runs]
        mean_hit, std_hit = _mean_std(best_hit_vals)
        mean_bal, std_bal = _mean_std(best_bal_vals)
        # choose representative best run by balanced_accuracy then hit_rate
        seed_runs.sort(
            key=lambda r: (
                float((r.get("best_profile") or {}).get("balanced_accuracy") or 0.0),
                float((r.get("best_profile") or {}).get("hit_rate") or 0.0),
            ),
            reverse=True,
        )
        rep = seed_runs[0] if seed_runs else {}
        eligible_runs = [
            r
            for r in seed_runs
            if _to_int((r.get("best_profile") or {}).get("matched"), 0) >= int(args.min_matched)
        ]
        rep_eligible = eligible_runs[0] if eligible_runs else {}
        eligible_hit_vals = [float((x.get("best_profile") or {}).get("hit_rate") or 0.0) for x in eligible_runs]
        eligible_bal_vals = [
            float((x.get("best_profile") or {}).get("balanced_accuracy") or 0.0) for x in eligible_runs
        ]
        eligible_hit_mean, eligible_hit_std = _mean_std(eligible_hit_vals)
        eligible_bal_mean, eligible_bal_std = _mean_std(eligible_bal_vals)
        eligibility_rate = (len(eligible_runs) / len(seed_runs)) if seed_runs else 0.0
        results.append(
            {
                "config_tag": tag,
                "window_bars": w,
                "horizon_bars": h,
                "stride": s,
                "dataset_id": dataset_id,
                "seeds": seeds,
                "seed_runs": seed_runs,
                "representative_best": rep,
                "best_profile_hit_rate_mean": round(mean_hit, 6),
                "best_profile_hit_rate_std": round(std_hit, 6),
                "best_profile_balanced_accuracy_mean": round(mean_bal, 6),
                "best_profile_balanced_accuracy_std": round(std_bal, 6),
                "ranking_min_matched": int(args.min_matched),
                "eligible_seed_runs": len(eligible_runs),
                "eligible_seed_rate": round(eligibility_rate, 6),
                "representative_best_eligible": rep_eligible,
                "eligible_best_profile_hit_rate_mean": round(eligible_hit_mean, 6),
                "eligible_best_profile_hit_rate_std": round(eligible_hit_std, 6),
                "eligible_best_profile_balanced_accuracy_mean": round(eligible_bal_mean, 6),
                "eligible_best_profile_balanced_accuracy_std": round(eligible_bal_std, 6),
            }
        )

    results.sort(
        key=lambda r: (
            float(r.get("eligible_seed_rate") or 0.0),
            float(r.get("eligible_best_profile_balanced_accuracy_mean") or 0.0),
            float(r.get("eligible_best_profile_hit_rate_mean") or 0.0),
        ),
        reverse=True,
    )

    report = {
        "schema": "blind_replay_dataset_grid_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "input_csv": str(args.input_csv.resolve()),
        "dataset_id": dataset_id,
        "sample_size": args.sample_size,
        "seeds": seeds,
        "profiles": [p.strip().upper() for p in str(args.profiles).split(",") if p.strip()],
        "ranking_policy": {
            "min_matched": int(args.min_matched),
            "sort_priority": [
                "eligible_seed_rate",
                "eligible_best_profile_balanced_accuracy_mean",
                "eligible_best_profile_hit_rate_mean",
            ],
        },
        "configs": results,
        "best_config": results[0] if results else None,
        "note": "Dataset-ablation report for B-track blind replay only.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    if results:
        bc = results[0]
        bp = (bc.get("representative_best_eligible") or {}).get("best_profile") or {}
        print(
            "best_config={tag} best_profile={p} bal_mean={bal} hit_mean={hit} eligible_rate={er}".format(
                tag=bc["config_tag"],
                p=bp.get("profile"),
                bal=bc.get("eligible_best_profile_balanced_accuracy_mean"),
                hit=bc.get("eligible_best_profile_hit_rate_mean"),
                er=bc.get("eligible_seed_rate"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
