#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preregistered Sasang 4-agent protocol ablation ([HYPO], synthetic ticks only).

Runs <=12 bias presets from ``sasang_4agent_protocol_ablation_register_v1.json`` on
deterministic synthetic ticks (no OHLCV / no timeseries file). Train/holdout split;
holdout MDD reduction vs control with bootstrap p-values and BH-FDR.

Does not promote Track A, fusion merge, oracle, or live trading.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / "docs/final/artifacts/sasang_4agent_protocol_ablation_register_v1.json"
DEFAULT_OUT = ROOT / "reports/sasang_4agent_protocol_ablation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_collision_module():
    path = ROOT / "scripts/run_sasang_4agent_collision_btrack_protocol_v1.py"
    spec = importlib.util.spec_from_file_location("sasang_collision_protocol", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _split_ticks(ticks: list[Any], holdout_fraction: float, min_holdout: int) -> tuple[list[Any], list[Any]]:
    n = len(ticks)
    if n < 2:
        return ticks, []
    hold_n = max(min_holdout, int(round(n * holdout_fraction)))
    hold_n = min(hold_n, n - 1)
    return ticks[: n - hold_n], ticks[n - hold_n :]


def _bh_fdr(p_values: list[float]) -> list[float]:
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adj = [1.0] * m
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        raw_rank = m - rank + 1
        val = min(prev, p_values[idx] * m / raw_rank)
        adj[idx] = val
        prev = val
    return adj


def _run_variant(
    mod: Any,
    ticks: list[Any],
    bias: dict[str, float],
    seed: int,
    bootstrap_trials: int,
) -> dict[str, Any]:
    run = mod._run_protocol(
        ticks=ticks,
        macro_window=float(bias["macro_window"]),
        mom_weight=float(bias["mom_weight"]),
        sim_thr=float(bias["similarity_threshold"]),
        defense_lambda=float(bias["defense_lambda"]),
        soeum_veto_threshold=float(bias["soeum_veto_threshold"]),
    )
    metrics = run["metrics"]
    p_boot = mod._bootstrap_p_value(
        baseline_returns=run["baseline_returns"],
        model_returns=run["model_returns"],
        observed_delta=float(metrics["mdd_reduction_abs"]),
        trials=bootstrap_trials,
        seed=seed,
    )
    return {
        **metrics,
        "mdd_reduction_p_value_bootstrap": p_boot,
    }


def build_ablation(
    register: dict[str, Any],
    *,
    bootstrap_trials: int = 200,
) -> dict[str, Any]:
    mod = _load_collision_module()
    split = register.get("split") if isinstance(register.get("split"), dict) else {}
    seed = int(split.get("seed", 42))
    ticks_n = int(split.get("ticks", 1200))
    holdout_fraction = float(split.get("holdout_fraction", 0.3))
    min_holdout = int(split.get("min_holdout_ticks", 120))

    all_ticks = mod._synthetic_ticks(seed=seed, n=max(300, ticks_n))
    train_ticks, holdout_ticks = _split_ticks(all_ticks, holdout_fraction, min_holdout)
    if len(holdout_ticks) < 30:
        raise RuntimeError("holdout tick count too small")

    variants = register.get("variants") if isinstance(register.get("variants"), list) else []
    control_id = str(register.get("control_id") or "A01_control_default")
    success = register.get("success_criteria") if isinstance(register.get("success_criteria"), dict) else {}
    min_delta = float(success.get("min_delta_vs_control", 0.005))
    max_p = float(success.get("max_bootstrap_p_lt", 0.05))

    results: list[dict[str, Any]] = []
    control_holdout_mdd: float | None = None

    for row in variants:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "")
        bias = row.get("bias_injection") if isinstance(row.get("bias_injection"), dict) else {}
        train_m = _run_variant(mod, train_ticks, bias, seed, bootstrap_trials)
        hold_m = _run_variant(mod, holdout_ticks, bias, seed + 17, bootstrap_trials)
        if vid == control_id:
            control_holdout_mdd = float(hold_m["mdd_reduction_abs"])
        results.append(
            {
                "id": vid,
                "label_ko": row.get("label_ko"),
                "theory_axes": row.get("theory_axes") or [],
                "bias_injection": bias,
                "train": train_m,
                "holdout": hold_m,
                "is_control": vid == control_id,
            }
        )

    if control_holdout_mdd is None:
        raise RuntimeError(f"control_id not found in variants: {control_id}")

    p_vs_control: list[float] = []
    for row in results:
        if row["is_control"]:
            row["holdout_delta_vs_control"] = 0.0
            row["holdout_beats_control"] = False
            p_vs_control.append(1.0)
            continue
        delta = float(row["holdout"]["mdd_reduction_abs"]) - control_holdout_mdd
        row["holdout_delta_vs_control"] = round(delta, 6)
        beats = delta >= min_delta and float(row["holdout"]["mdd_reduction_p_value_bootstrap"]) < max_p
        row["holdout_beats_control"] = beats
        p_vs_control.append(float(row["holdout"]["mdd_reduction_p_value_bootstrap"]))

    fdr = _bh_fdr(p_vs_control)
    n_exploratory_pass = 0
    for row, q in zip(results, fdr):
        row["holdout_p_fdr_bh"] = round(q, 6) if not row["is_control"] else None
        if row["is_control"]:
            row["exploratory_pass"] = False
            continue
        pass_row = (
            float(row["holdout_delta_vs_control"]) >= min_delta
            and float(row["holdout"]["mdd_reduction_p_value_bootstrap"]) < max_p
            and q < max_p
        )
        row["exploratory_pass"] = pass_row
        if pass_row:
            n_exploratory_pass += 1

    non_control = [r for r in results if not r["is_control"]]
    best = max(non_control, key=lambda r: float(r["holdout"]["mdd_reduction_abs"])) if non_control else None

    verdict = (
        "null_under_preregistered_gates"
        if n_exploratory_pass == 0
        else "exploratory_pass_candidate"
    )

    track_wall = register.get("track_wall") if isinstance(register.get("track_wall"), dict) else {}

    return {
        "schema": "sasang_4agent_protocol_ablation_v1",
        "generated_at_utc": _utc(),
        "mode": "research_only",
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": register.get("rq_id"),
        "register_path": str(DEFAULT_REGISTER).replace("\\", "/"),
        "h0": register.get("h0"),
        "data_policy": register.get("data_policy"),
        "experiment": {
            "seed": seed,
            "ticks_total": len(all_ticks),
            "ticks_train": len(train_ticks),
            "ticks_holdout": len(holdout_ticks),
            "holdout_fraction": holdout_fraction,
            "bootstrap_trials": bootstrap_trials,
            "data_mode": "synthetic_ticks_only",
        },
        "success_criteria": success,
        "control_id": control_id,
        "control_holdout_mdd_reduction_abs": control_holdout_mdd,
        "n_variants": len(results),
        "n_exploratory_pass": n_exploratory_pass,
        "verdict": verdict,
        "best_holdout_mdd_id_exploratory_only": best["id"] if best else None,
        "variants": results,
        "track_wall": {
            **track_wall,
            "fusion_pipeline_merge_allowed": False,
            "track_a_promotion": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--register-json", type=Path, default=DEFAULT_REGISTER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bootstrap-trials", type=int, default=200)
    ap.add_argument("--ticks", type=int, default=0, help="Override register split ticks")
    args = ap.parse_args()

    if not args.register_json.is_file():
        print(f"missing register: {args.register_json}", file=sys.stderr)
        return 2

    register = json.loads(args.register_json.read_text(encoding="utf-8"))
    if args.ticks > 0:
        split = register.setdefault("split", {})
        if isinstance(split, dict):
            split["ticks"] = args.ticks

    payload = build_ablation(register, bootstrap_trials=max(50, args.bootstrap_trials))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json.resolve()))
    print(f"verdict={payload['verdict']} n_exploratory_pass={payload['n_exploratory_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
