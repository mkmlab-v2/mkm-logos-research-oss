#!/usr/bin/env python3
"""Sweep bridge confidence parameters and select holdout-safe size uplift candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_ENSEMBLE = ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"
HOLDOUT_SCRIPT = ROOT / "scripts" / "run_compression_bridge_size_holdout_eval_v1.py"
OUT_PATH = ROOT / "docs" / "final" / "artifacts" / "compression_bridge_size_tuning_sweep_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _set_rules(
    base_cfg: dict[str, Any],
    *,
    signal_scale: float,
    negative_cap: float,
    quality_bonus_scale: float,
    policy_gap_penalty_scale: float,
) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base_cfg, ensure_ascii=False))
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    cfg["rules"] = rules
    rules["compression_bridge_signal_scale"] = float(signal_scale)
    rules["compression_bridge_positive_signal_cap"] = float(rules.get("compression_bridge_positive_signal_cap", 0.03))
    rules["compression_bridge_negative_signal_cap"] = float(negative_cap)
    rules["compression_bridge_quality_bonus_scale"] = float(quality_bonus_scale)
    rules["compression_bridge_policy_gap_penalty_scale"] = float(policy_gap_penalty_scale)
    rules["compression_bridge_policy_target_saving"] = float(rules.get("compression_bridge_policy_target_saving", 0.49))
    rules["compression_bridge_quality_anchor_jaccard"] = float(rules.get("compression_bridge_quality_anchor_jaccard", 0.80))
    rules["compression_bridge_integrity_required_for_bonus"] = True
    return cfg


def _score_candidate(holdout_doc: dict[str, Any]) -> tuple[bool, float]:
    rows = holdout_doc.get("rows") if isinstance(holdout_doc.get("rows"), list) else []
    ok_rows = [r for r in rows if isinstance(r, dict) and r.get("status") == "ok"]
    if not ok_rows:
        return False, -999.0
    any_bad_dir = any((r.get("prediction_direction_on") != r.get("prediction_direction_off")) for r in ok_rows)
    any_bad_hit = any(_f(r.get("delta_price_directional_hit_rate")) < 0.0 for r in ok_rows)
    mean_size_weighted = sum(_f(r.get("delta_size_weighted_payoff_mean")) for r in ok_rows) / len(ok_rows)
    feasible = (not any_bad_dir) and (not any_bad_hit)
    return feasible, mean_size_weighted


def main() -> int:
    ap = argparse.ArgumentParser(description="Search holdout-safe bridge confidence parameters.")
    ap.add_argument("--base-ensemble-config", type=Path, default=BASE_ENSEMBLE)
    ap.add_argument("--windows", type=str, default="30,60,120")
    ap.add_argument("--signal-scales", type=str, default="0.5,1.0,1.5,2.0,3.0")
    ap.add_argument("--negative-caps", type=str, default="0.0,0.005,0.01,0.02")
    ap.add_argument("--quality-bonus-scales", type=str, default="0.15,0.2,0.3,0.4")
    ap.add_argument("--policy-gap-penalty-scales", type=str, default="0.1,0.2,0.3,0.4")
    ap.add_argument("--output", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    if not args.base_ensemble_config.is_file():
        print(f"missing base ensemble config: {args.base_ensemble_config}", file=sys.stderr)
        return 1
    base_cfg = _load_json(args.base_ensemble_config)

    try:
        scales = [float(x.strip()) for x in args.signal_scales.split(",") if x.strip()]
        neg_caps = [float(x.strip()) for x in args.negative_caps.split(",") if x.strip()]
        q_scales = [float(x.strip()) for x in args.quality_bonus_scales.split(",") if x.strip()]
        p_scales = [float(x.strip()) for x in args.policy_gap_penalty_scales.split(",") if x.strip()]
    except ValueError as exc:
        print(f"invalid float grid: {exc}", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bridge_size_tune_") as td:
        tdp = Path(td)
        for s in scales:
            for ncap in neg_caps:
                for q in q_scales:
                    for p in p_scales:
                        cfg = _set_rules(
                            base_cfg,
                            signal_scale=s,
                            negative_cap=ncap,
                            quality_bonus_scale=q,
                            policy_gap_penalty_scale=p,
                        )
                        cfg_path = tdp / f"cfg_s{s}_n{ncap}_q{q}_p{p}.json"
                        out_path = tdp / f"holdout_s{s}_n{ncap}_q{q}_p{p}.json"
                        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                        rc, out, err = _run(
                            [
                                sys.executable,
                                str(HOLDOUT_SCRIPT),
                                "--windows",
                                args.windows,
                                "--ensemble-config",
                                str(cfg_path),
                                "--output",
                                str(out_path),
                            ]
                        )
                        if rc != 0:
                            rows.append(
                                {
                                    "signal_scale": s,
                                    "negative_cap": ncap,
                                    "quality_bonus_scale": q,
                                    "policy_gap_penalty_scale": p,
                                    "status": "error",
                                    "error": (err or out).strip()[:600],
                                }
                            )
                            continue
                        holdout = _load_json(out_path)
                        feasible, score = _score_candidate(holdout)
                        summary = holdout.get("summary") if isinstance(holdout.get("summary"), dict) else {}
                        rows.append(
                            {
                                "signal_scale": s,
                                "negative_cap": ncap,
                                "quality_bonus_scale": q,
                                "policy_gap_penalty_scale": p,
                                "status": "ok",
                                "feasible": feasible,
                                "mean_delta_size_weighted_payoff": round(score, 8),
                                "direction_changed_rows": summary.get("direction_changed_rows"),
                                "hit_rate_uplift_rows": summary.get("hit_rate_uplift_rows"),
                                "size_weighted_payoff_uplift_rows": summary.get("size_weighted_payoff_uplift_rows"),
                                "size_weighted_payoff_degrade_rows": summary.get("size_weighted_payoff_degrade_rows"),
                                "holdout_artifact": str(out_path),
                            }
                        )

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    feasible_rows = [r for r in ok_rows if bool(r.get("feasible"))]
    best = None
    if feasible_rows:
        best = sorted(
            feasible_rows,
            key=lambda r: (
                _f(r.get("mean_delta_size_weighted_payoff")),
                int(r.get("size_weighted_payoff_uplift_rows") or 0),
                -int(r.get("size_weighted_payoff_degrade_rows") or 0),
            ),
            reverse=True,
        )[0]

    out = {
        "schema": "compression_bridge_size_tuning_sweep_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "base_ensemble_config": str(args.base_ensemble_config.resolve()),
            "windows": args.windows,
            "signal_scales": scales,
            "negative_caps": neg_caps,
            "quality_bonus_scales": q_scales,
            "policy_gap_penalty_scales": p_scales,
        },
        "rows": rows,
        "best_feasible_candidate": best,
        "decision": "FOUND_HOLDOUT_SAFE_UPLIFT" if (best and _f(best.get("mean_delta_size_weighted_payoff")) > 0.0) else "NO_HOLDOUT_SAFE_UPLIFT",
        "fact_safe_note": "Requires re-run confirmation on persisted artifact after applying best candidate.",
        "out_of_scope": "No live trigger and no automatic promotion.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

