#!/usr/bin/env python3
"""Build unified BTC/KOSPI profile scoreboard from blind replay outputs."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLIND_DIR = ROOT / "reports" / "constitution" / "btrack_pilot" / "blind_replay"
SWEEP_SCRIPT = ROOT / "scripts" / "run_blind_replay_profile_sweep.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def _mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _weighted_sigma(values: dict[str, float], weights: dict[str, float]) -> float:
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.0
    mu = sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w
    var = sum(weights[k] * ((values.get(k, 0.0) - mu) ** 2) for k in weights) / total_w
    return math.sqrt(max(0.0, var))


def _resolve_asset_runs(grid_path: Path) -> tuple[str, str, list[int], list[tuple[Path, Path]]]:
    grid = _read_json(grid_path)
    best_cfg = grid.get("best_config") if isinstance(grid.get("best_config"), dict) else {}
    tag = str(best_cfg.get("config_tag") or "")
    if not tag:
        raise SystemExit(f"best_config missing in {grid_path}")
    dataset_id = str(grid.get("dataset_id") or best_cfg.get("dataset_id") or "").strip()
    seeds = best_cfg.get("seeds") if isinstance(best_cfg.get("seeds"), list) else []
    seed_ids = [int(x) for x in seeds]
    runs: list[tuple[Path, Path]] = []
    for seed in seed_ids:
        if dataset_id:
            seed_tag = f"{dataset_id}_{tag}_seed{seed}"
        else:
            seed_tag = f"{tag}_seed{seed}"
        public_path = BLIND_DIR / f"blind_replay_public_{seed_tag}.jsonl"
        key_path = BLIND_DIR / f"blind_replay_answer_key_{seed_tag}.jsonl"
        if not public_path.is_file() or not key_path.is_file():
            raise SystemExit(f"missing seed run files: {public_path} / {key_path}")
        runs.append((public_path, key_path))
    return tag, dataset_id, seed_ids, runs


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Aegis unified BTC/KOSPI scoreboard.")
    ap.add_argument("--btc-grid", type=Path, required=True)
    ap.add_argument("--kospi-grid", type=Path, required=True)
    ap.add_argument("--profiles", default="A,B,C")
    ap.add_argument("--w-btc", type=float, default=0.7)
    ap.add_argument("--w-kospi", type=float, default=0.3)
    ap.add_argument("--kappa", type=float, default=0.15)
    ap.add_argument("--shadow-w-btc", type=float, default=0.6)
    ap.add_argument("--shadow-w-kospi", type=float, default=0.4)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "aegis_unified_scoreboard_latest.json",
    )
    args = ap.parse_args()

    profiles = [p.strip().upper() for p in str(args.profiles).split(",") if p.strip()]
    if not profiles:
        raise SystemExit("No profiles specified")

    btc_tag, btc_dataset_id, btc_seeds, btc_runs = _resolve_asset_runs(args.btc_grid)
    kospi_tag, kospi_dataset_id, kospi_seeds, kospi_runs = _resolve_asset_runs(args.kospi_grid)

    per_asset_per_profile: dict[str, dict[str, dict[str, list[float]]]] = {
        "BTC": {p: {"hit": [], "bal": [], "matched": []} for p in profiles},
        "KOSPI": {p: {"hit": [], "bal": [], "matched": []} for p in profiles},
    }

    tmp_dir = BLIND_DIR / "unified_scoreboard_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for asset, runs in (("BTC", btc_runs), ("KOSPI", kospi_runs)):
        for idx, (public_path, key_path) in enumerate(runs, start=1):
            out_path = tmp_dir / f"ranking_{asset.lower()}_{idx:03d}.json"
            _run(
                [
                    sys.executable,
                    str(SWEEP_SCRIPT),
                    "--public-dataset",
                    str(public_path),
                    "--answer-key",
                    str(key_path),
                    "--profiles",
                    ",".join(profiles),
                    "--out",
                    str(out_path),
                ]
            )
            sweep = _read_json(out_path)
            rows = sweep.get("profiles") if isinstance(sweep.get("profiles"), list) else []
            for row in rows:
                profile = str(row.get("profile") or "").upper()
                if profile not in per_asset_per_profile[asset]:
                    continue
                per_asset_per_profile[asset][profile]["hit"].append(float(row.get("hit_rate") or 0.0))
                per_asset_per_profile[asset][profile]["bal"].append(float(row.get("balanced_accuracy") or 0.0))
                per_asset_per_profile[asset][profile]["matched"].append(float(row.get("matched") or 0.0))

    baseline_weights = {"BTC": float(args.w_btc), "KOSPI": float(args.w_kospi)}
    shadow_weights = {"BTC": float(args.shadow_w_btc), "KOSPI": float(args.shadow_w_kospi)}

    ranking_rows: list[dict[str, Any]] = []
    for p in profiles:
        btc_hit = _mean(per_asset_per_profile["BTC"][p]["hit"])
        btc_bal = _mean(per_asset_per_profile["BTC"][p]["bal"])
        kospi_hit = _mean(per_asset_per_profile["KOSPI"][p]["hit"])
        kospi_bal = _mean(per_asset_per_profile["KOSPI"][p]["bal"])
        btc_n = int(round(_mean(per_asset_per_profile["BTC"][p]["matched"])))
        kospi_n = int(round(_mean(per_asset_per_profile["KOSPI"][p]["matched"])))

        base_mu_bal = (
            baseline_weights["BTC"] * btc_bal + baseline_weights["KOSPI"] * kospi_bal
        ) / (baseline_weights["BTC"] + baseline_weights["KOSPI"])
        base_mu_hit = (
            baseline_weights["BTC"] * btc_hit + baseline_weights["KOSPI"] * kospi_hit
        ) / (baseline_weights["BTC"] + baseline_weights["KOSPI"])
        base_sigma_bal = _weighted_sigma({"BTC": btc_bal, "KOSPI": kospi_bal}, baseline_weights)
        base_sigma_hit = _weighted_sigma({"BTC": btc_hit, "KOSPI": kospi_hit}, baseline_weights)
        base_score_bal = base_mu_bal - float(args.kappa) * base_sigma_bal
        base_score_hit = base_mu_hit - float(args.kappa) * base_sigma_hit

        shadow_mu_bal = (
            shadow_weights["BTC"] * btc_bal + shadow_weights["KOSPI"] * kospi_bal
        ) / (shadow_weights["BTC"] + shadow_weights["KOSPI"])
        shadow_sigma_bal = _weighted_sigma({"BTC": btc_bal, "KOSPI": kospi_bal}, shadow_weights)
        shadow_score_bal = shadow_mu_bal - float(args.kappa) * shadow_sigma_bal

        ranking_rows.append(
            {
                "profile": p,
                "asset_metrics": {
                    "BTC": {"hit_rate_mean": round(btc_hit, 6), "balanced_accuracy_mean": round(btc_bal, 6), "matched_mean": btc_n},
                    "KOSPI": {
                        "hit_rate_mean": round(kospi_hit, 6),
                        "balanced_accuracy_mean": round(kospi_bal, 6),
                        "matched_mean": kospi_n,
                    },
                },
                "baseline_7_3": {
                    "mu_balanced": round(base_mu_bal, 6),
                    "sigma_balanced": round(base_sigma_bal, 6),
                    "unified_score_balanced": round(base_score_bal, 6),
                    "mu_hit": round(base_mu_hit, 6),
                    "sigma_hit": round(base_sigma_hit, 6),
                    "unified_score_hit": round(base_score_hit, 6),
                },
                "shadow_6_4": {
                    "mu_balanced": round(shadow_mu_bal, 6),
                    "sigma_balanced": round(shadow_sigma_bal, 6),
                    "unified_score_balanced": round(shadow_score_bal, 6),
                },
                "delta_7_3_minus_6_4_balanced": round(base_score_bal - shadow_score_bal, 6),
            }
        )

    ranking_rows.sort(
        key=lambda x: (
            float(((x.get("baseline_7_3") or {}).get("unified_score_balanced") or 0.0)),
            float(((x.get("baseline_7_3") or {}).get("unified_score_hit") or 0.0)),
        ),
        reverse=True,
    )

    payload = {
        "schema": "aegis_unified_scoreboard_v1_1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "inputs": {
            "btc_grid": str(args.btc_grid.resolve()),
            "kospi_grid": str(args.kospi_grid.resolve()),
            "btc_best_config_tag": btc_tag,
            "btc_dataset_id": btc_dataset_id,
            "kospi_best_config_tag": kospi_tag,
            "kospi_dataset_id": kospi_dataset_id,
            "btc_seeds": btc_seeds,
            "kospi_seeds": kospi_seeds,
            "profiles": profiles,
        },
        "weights": {
            "baseline_7_3": baseline_weights,
            "shadow_6_4": shadow_weights,
            "kappa": float(args.kappa),
        },
        "ranking": ranking_rows,
        "ace_profile": ranking_rows[0] if ranking_rows else None,
        "note": "Unified profile scoreboard for BTC-first operating mode.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    if ranking_rows:
        top = ranking_rows[0]
        print(
            "ace_profile={p} unified_bal_7_3={s}".format(
                p=top.get("profile"),
                s=((top.get("baseline_7_3") or {}).get("unified_score_balanced")),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

