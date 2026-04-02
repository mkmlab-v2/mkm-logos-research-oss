#!/usr/bin/env python3
"""Build regime-conditional profile policy and score simulation."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "blind_replay_regime_split_benchmark_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "blind_replay_regime_conditional_selection_latest.json"


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


def _get_bal(asset_doc: dict[str, Any], profile: str, bucket: str) -> float:
    return float(
        ((((asset_doc.get("profiles") or {}).get(profile) or {}).get(bucket) or {}).get("balanced_accuracy") or {}).get(
            "mean",
            0.0,
        )
    )


def _best_profile(asset_doc: dict[str, Any], bucket: str) -> str:
    profiles = asset_doc.get("profiles") if isinstance(asset_doc.get("profiles"), dict) else {}
    cand: list[tuple[float, str]] = []
    for p in ("A", "B", "C"):
        bal = float((((profiles.get(p) or {}).get(bucket) or {}).get("balanced_accuracy") or {}).get("mean") or 0.0)
        cand.append((bal, p))
    cand.sort(reverse=True)
    return cand[0][1] if cand else "A"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build regime-conditional profile selection policy.")
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--w-btc", type=float, default=0.7)
    ap.add_argument("--w-kospi", type=float, default=0.3)
    ap.add_argument("--kappa", type=float, default=0.15)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = _read_json(args.in_path)
    assets = src.get("assets") if isinstance(src.get("assets"), dict) else {}
    btc = assets.get("BTC") if isinstance(assets.get("BTC"), dict) else {}
    kospi = assets.get("KOSPI") if isinstance(assets.get("KOSPI"), dict) else {}

    btc_low = _best_profile(btc, "LOW_VOL")
    btc_high = _best_profile(btc, "HIGH_VOL")
    kospi_low = _best_profile(kospi, "LOW_VOL")
    kospi_high = _best_profile(kospi, "HIGH_VOL")

    # Static baseline: single best profile by average (LOW/HIGH) per asset.
    static_asset_profile: dict[str, str] = {}
    for asset_name, asset_doc in (("BTC", btc), ("KOSPI", kospi)):
        best_p = "A"
        best_avg = -1.0
        for p in ("A", "B", "C"):
            low = _get_bal(asset_doc, p, "LOW_VOL")
            high = _get_bal(asset_doc, p, "HIGH_VOL")
            avg = (low + high) / 2.0
            if avg > best_avg:
                best_avg = avg
                best_p = p
        static_asset_profile[asset_name] = best_p

    cond_bal = {
        "BTC": (_get_bal(btc, btc_low, "LOW_VOL") + _get_bal(btc, btc_high, "HIGH_VOL")) / 2.0,
        "KOSPI": (_get_bal(kospi, kospi_low, "LOW_VOL") + _get_bal(kospi, kospi_high, "HIGH_VOL")) / 2.0,
    }
    static_bal = {
        "BTC": (
            _get_bal(btc, static_asset_profile["BTC"], "LOW_VOL")
            + _get_bal(btc, static_asset_profile["BTC"], "HIGH_VOL")
        )
        / 2.0,
        "KOSPI": (
            _get_bal(kospi, static_asset_profile["KOSPI"], "LOW_VOL")
            + _get_bal(kospi, static_asset_profile["KOSPI"], "HIGH_VOL")
        )
        / 2.0,
    }

    weights = {"BTC": float(args.w_btc), "KOSPI": float(args.w_kospi)}
    cond_mu = (weights["BTC"] * cond_bal["BTC"] + weights["KOSPI"] * cond_bal["KOSPI"]) / (
        weights["BTC"] + weights["KOSPI"]
    )
    cond_sigma = _weighted_sigma(cond_bal, weights)
    cond_unified = cond_mu - float(args.kappa) * cond_sigma

    static_mu = (weights["BTC"] * static_bal["BTC"] + weights["KOSPI"] * static_bal["KOSPI"]) / (
        weights["BTC"] + weights["KOSPI"]
    )
    static_sigma = _weighted_sigma(static_bal, weights)
    static_unified = static_mu - float(args.kappa) * static_sigma

    out = {
        "schema": "blind_replay_regime_conditional_selection_v1",
        "generated_at_utc": _utc_now(),
        "exploratory_only": True,
        "a_track_binding_forbidden": True,
        "source_report": str(args.in_path.resolve()),
        "weights": {"w_btc": float(args.w_btc), "w_kospi": float(args.w_kospi), "kappa": float(args.kappa)},
        "policy": {
            "BTC": {"LOW_VOL": btc_low, "HIGH_VOL": btc_high},
            "KOSPI": {"LOW_VOL": kospi_low, "HIGH_VOL": kospi_high},
        },
        "static_baseline": {
            "single_profile_per_asset": static_asset_profile,
            "asset_balanced_accuracy_mean": {k: round(v, 6) for k, v in static_bal.items()},
            "unified_score_balanced": round(static_unified, 6),
        },
        "conditional_simulation": {
            "asset_balanced_accuracy_mean": {k: round(v, 6) for k, v in cond_bal.items()},
            "unified_score_balanced": round(cond_unified, 6),
        },
        "delta_conditional_minus_static": round(cond_unified - static_unified, 6),
        "note": "Regime-conditional profile selection from LOW/HIGH volatility split benchmark.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(
        "policy_btc=({low}/{high}) policy_kospi=({kl}/{kh}) delta={d}".format(
            low=btc_low,
            high=btc_high,
            kl=kospi_low,
            kh=kospi_high,
            d=out["delta_conditional_minus_static"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

