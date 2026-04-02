#!/usr/bin/env python3
"""Sweep anchor weights/kappa on existing unified scoreboard metrics."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "aegis_unified_scoreboard_abcds_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "aegis_anchor_weight_sweep_latest.json"


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


def _weighted_sigma(values: dict[str, float], weights: dict[str, float]) -> float:
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.0
    mu = sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w
    var = sum(weights[k] * ((values.get(k, 0.0) - mu) ** 2) for k in weights) / total_w
    return math.sqrt(max(0.0, var))


def _frange(start: float, stop: float, step: float) -> list[float]:
    vals: list[float] = []
    x = start
    while x <= stop + 1e-12:
        vals.append(round(x, 6))
        x += step
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep (w_btc, kappa) on existing profile metrics.")
    ap.add_argument("--in-scoreboard", type=Path, default=DEFAULT_IN)
    ap.add_argument("--w-btc-min", type=float, default=0.6)
    ap.add_argument("--w-btc-max", type=float, default=0.9)
    ap.add_argument("--w-btc-step", type=float, default=0.05)
    ap.add_argument("--kappa-min", type=float, default=0.1)
    ap.add_argument("--kappa-max", type=float, default=0.2)
    ap.add_argument("--kappa-step", type=float, default=0.01)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = _read_json(args.in_scoreboard)
    rows = src.get("ranking") if isinstance(src.get("ranking"), list) else []
    if not rows:
        raise SystemExit(f"No ranking rows found: {args.in_scoreboard}")

    profiles: list[dict[str, Any]] = []
    for row in rows:
        asset = row.get("asset_metrics") if isinstance(row.get("asset_metrics"), dict) else {}
        btc = asset.get("BTC") if isinstance(asset.get("BTC"), dict) else {}
        kospi = asset.get("KOSPI") if isinstance(asset.get("KOSPI"), dict) else {}
        profiles.append(
            {
                "profile": str(row.get("profile") or ""),
                "btc_bal": float(btc.get("balanced_accuracy_mean") or 0.0),
                "kospi_bal": float(kospi.get("balanced_accuracy_mean") or 0.0),
                "btc_hit": float(btc.get("hit_rate_mean") or 0.0),
                "kospi_hit": float(kospi.get("hit_rate_mean") or 0.0),
            }
        )

    trials: list[dict[str, Any]] = []
    for w_btc in _frange(args.w_btc_min, args.w_btc_max, args.w_btc_step):
        w_kospi = round(1.0 - w_btc, 6)
        weights = {"BTC": w_btc, "KOSPI": w_kospi}
        for kappa in _frange(args.kappa_min, args.kappa_max, args.kappa_step):
            ranked: list[dict[str, Any]] = []
            for p in profiles:
                mu_bal = (weights["BTC"] * p["btc_bal"] + weights["KOSPI"] * p["kospi_bal"]) / (
                    weights["BTC"] + weights["KOSPI"]
                )
                sigma_bal = _weighted_sigma({"BTC": p["btc_bal"], "KOSPI": p["kospi_bal"]}, weights)
                score_bal = mu_bal - kappa * sigma_bal
                ranked.append(
                    {
                        "profile": p["profile"],
                        "unified_score_balanced": round(score_bal, 6),
                        "mu_balanced": round(mu_bal, 6),
                        "sigma_balanced": round(sigma_bal, 6),
                    }
                )
            ranked.sort(key=lambda x: float(x["unified_score_balanced"]), reverse=True)
            top = ranked[0]
            trials.append(
                {
                    "w_btc": round(w_btc, 6),
                    "w_kospi": round(w_kospi, 6),
                    "kappa": round(kappa, 6),
                    "ace_profile": top["profile"],
                    "ace_unified_score_balanced": top["unified_score_balanced"],
                    "top3": ranked[:3],
                }
            )

    trials.sort(key=lambda x: float(x["ace_unified_score_balanced"]), reverse=True)
    best = trials[0]
    payload = {
        "schema": "aegis_anchor_weight_sweep_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "input_scoreboard": str(args.in_scoreboard.resolve()),
        "search_space": {
            "w_btc_min": float(args.w_btc_min),
            "w_btc_max": float(args.w_btc_max),
            "w_btc_step": float(args.w_btc_step),
            "kappa_min": float(args.kappa_min),
            "kappa_max": float(args.kappa_max),
            "kappa_step": float(args.kappa_step),
        },
        "trial_count": len(trials),
        "best": best,
        "top20": trials[:20],
        "note": "Weight/kappa sweep on frozen profile metrics (no retraining).",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(
        "BEST w_btc={w} kappa={k} ace={p} score={s}".format(
            w=best["w_btc"], k=best["kappa"], p=best["ace_profile"], s=best["ace_unified_score_balanced"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

