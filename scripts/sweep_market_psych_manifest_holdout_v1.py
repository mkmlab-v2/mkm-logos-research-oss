#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holdout sweep for market_psych v2 manifest axis weights (train select / holdout report)."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _actual_direction,
    _daily_return,
    _row_pair_for_eval_date,
)
from scripts.market_psych_sasang_axis_v2 import (  # noqa: E402
    load_manifest,
    map_row_to_sasang,
    validate_psych_csv_fields,
)

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"
DEFAULT_PSYCH = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/market_psych_manifest_holdout_sweep_v1_latest.json"
CANDIDATE_OUT = ROOT / "reports/market_psych_manifest_candidate_holdout_best_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_ohlc(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = str(row.get("date") or row.get("Date") or "")[:10]
            if len(d) != 10:
                continue
            try:
                c = float(row.get("close") or row.get("Close") or 0)
            except (TypeError, ValueError):
                continue
            rows.append({"date": d, "close": c})
    rows.sort(key=lambda r: r["date"])
    return rows


def _scale_weights(
    manifest: dict[str, Any],
    axis: str,
    keys: list[str],
    factor: float,
) -> dict[str, Any]:
    out = copy.deepcopy(manifest)
    wmap = out.setdefault("axis_raw_weights", {}).setdefault(axis, {})
    for k in keys:
        if k in wmap:
            wmap[k] = round(float(wmap[k]) * factor, 8)
    return out


def _candidate_manifests(base: dict[str, Any]) -> list[dict[str, Any]]:
    ty_hot = ["heat_proxy", "greed_score", "fomo_index", "ret_5d_pos"]
    te_cold = ["fear_score", "panic_ratio", "cold_proxy", "drawdown_20d"]
    sy_vol = ["dispersion_score", "vol_ratio_dev", "vol_structure_proxy", "trend_strength"]
    se_calm = ["calm_inverse_vol", "low_panic", "rsi_neutral", "cold_proxy"]

    specs: list[dict[str, Any]] = [{"profile_id": "baseline", "neutral_band": 0.06}]
    for nb in (0.05, 0.07, 0.08):
        specs.append({"profile_id": f"nb_{int(nb * 100):03d}", "neutral_band": nb})
    for f in (1.15, 1.25):
        specs.append(
            {
                "profile_id": f"ty_hot_x{int(f * 100)}",
                "neutral_band": 0.06,
                "scales": [( "TY", ty_hot, f)],
            }
        )
    for f in (1.15, 1.25):
        specs.append(
            {
                "profile_id": f"te_cold_x{int(f * 100)}",
                "neutral_band": 0.06,
                "scales": [("TE", te_cold, f)],
            }
        )
    for f in (1.1, 1.2):
        specs.append(
            {
                "profile_id": f"sy_vol_x{int(f * 100)}",
                "neutral_band": 0.06,
                "scales": [("SY", sy_vol, f)],
            }
        )
    specs.append(
        {
            "profile_id": "combo_ty_te_boost",
            "neutral_band": 0.06,
            "scales": [("TY", ty_hot, 1.2), ("TE", te_cold, 1.2)],
        }
    )
    specs.append(
        {
            "profile_id": "combo_defensive",
            "neutral_band": 0.07,
            "scales": [("TE", te_cold, 1.25), ("SE", se_calm, 1.15)],
        }
    )

    out: list[dict[str, Any]] = []
    for spec in specs:
        m = copy.deepcopy(base)
        for axis, keys, factor in spec.get("scales") or []:
            m = _scale_weights(m, axis, list(keys), float(factor))
        out.append(
            {
                "profile_id": spec["profile_id"],
                "neutral_band": float(spec.get("neutral_band", 0.06)),
                "manifest": m,
            }
        )
    return out


def _per_date_from_psych(
    psych_csv: Path,
    manifest: dict[str, Any],
    neutral_band: float,
) -> dict[str, str]:
    pred: dict[str, str] = {}
    prev_stress: float | None = None
    with psych_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_psych_csv_fields(reader.fieldnames, manifest)
        for row in reader:
            ts = str(row.get("timestamp_utc") or "")[:10]
            if len(ts) != 10:
                continue
            mapped = map_row_to_sasang(
                row,
                manifest=manifest,
                neutral_band=neutral_band,
                prev_stress=prev_stress,
            )
            prev_stress = float(mapped["byungjeung"]["stress_index"])
            pred[ts] = str(mapped["predicted_direction"])
    return pred


def _verdict_ko(best: dict[str, Any] | None) -> str:
    if not best:
        return "no train hit rate"
    tr = best.get("train") or {}
    ho = best.get("holdout") or {}
    tr_r = tr.get("kospi_hit_rate")
    ho_r = ho.get("kospi_hit_rate")
    if tr_r is None:
        return "no train hit rate"
    tr_pct = f"{100.0 * float(tr_r):.1f}%"
    ho_pct = f"{100.0 * float(ho_r):.1f}%" if ho_r is not None else "n/a"
    return (
        f"train 최고={best['profile_id']} KOSPI {tr_pct} "
        f"(holdout {ho_pct}, n={ho.get('n_evaluated')}). "
        "후보 manifest는 reports/*_candidate_* — SSOT 덮어쓰기 전 휴먼 sign-off. B-track only."
    )


def _kospi_hit(
    pred_by_date: dict[str, str],
    ohlc: list[dict[str, Any]],
    eval_dates: list[str],
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    hits = 0
    n = 0
    skipped_neutral_pred = 0
    for d in eval_dates:
        pd = pred_by_date.get(d)
        if not pd:
            continue
        if pd == "neutral":
            skipped_neutral_pred += 1
            continue
        pair = _row_pair_for_eval_date(ohlc, d)
        if pair is None:
            continue
        ret = _daily_return(pair[0], pair[1])
        act = _actual_direction(ret, neutral_bps)
        if act == "neutral":
            continue
        n += 1
        if pd == act:
            hits += 1
    rate = (hits / n) if n else None
    return {
        "kospi_hit_rate": round(rate, 6) if rate is not None else None,
        "n_evaluated": n,
        "price_hits": hits,
        "skipped_neutral_pred": skipped_neutral_pred,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--psych-csv", type=Path, default=DEFAULT_PSYCH)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--base-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--holdout-days", type=int, default=72)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-candidate", type=Path, default=CANDIDATE_OUT)
    args = ap.parse_args()

    if not args.psych_csv.is_file():
        print(f"missing {args.psych_csv}", file=sys.stderr)
        return 2
    if not args.kospi_csv.is_file():
        print(f"missing {args.kospi_csv}", file=sys.stderr)
        return 2

    base = load_manifest(args.base_manifest)
    ohlc = _load_ohlc(args.kospi_csv)
    if len(ohlc) < 10:
        print("kospi ohlc too short", file=sys.stderr)
        return 2

    pred_dates = sorted(_per_date_from_psych(args.psych_csv, base, 0.06).keys())
    ohlc_dates = {r["date"] for r in ohlc}
    eligible = [d for d in pred_dates if d in ohlc_dates]
    if len(eligible) < args.holdout_days + 30:
        print("not enough overlapping dates", file=sys.stderr)
        return 2

    holdout = eligible[-args.holdout_days :]
    train = [d for d in eligible if d not in set(holdout)]

    candidates = _candidate_manifests(base)
    rows: list[dict[str, Any]] = []
    for cand in candidates:
        pred = _per_date_from_psych(args.psych_csv, cand["manifest"], cand["neutral_band"])
        tr = _kospi_hit(pred, ohlc, train, args.neutral_bps)
        ho = _kospi_hit(pred, ohlc, holdout, args.neutral_bps)
        rows.append(
            {
                "profile_id": cand["profile_id"],
                "neutral_band": cand["neutral_band"],
                "train": tr,
                "holdout": ho,
            }
        )

    def _train_key(r: dict[str, Any]) -> float:
        v = (r.get("train") or {}).get("kospi_hit_rate")
        return float(v) if v is not None else -1.0

    rows.sort(key=_train_key, reverse=True)
    best = rows[0] if rows else None
    baseline_row = next((r for r in rows if r["profile_id"] == "baseline"), None)

    winner_spec = next((c for c in candidates if c["profile_id"] == best["profile_id"]), None) if best else None
    if winner_spec:
        cand_doc = copy.deepcopy(winner_spec["manifest"])
        cand_doc["holdout_learning_v1"] = {
            "selected_on": "train_kospi_hit_rate",
            "profile_id": winner_spec["profile_id"],
            "neutral_band": winner_spec["neutral_band"],
            "train_n": (best.get("train") or {}).get("n_evaluated"),
            "holdout_n": (best.get("holdout") or {}).get("n_evaluated"),
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "not_ssot_until_human_signoff": True,
        }
        args.write_candidate.parent.mkdir(parents=True, exist_ok=True)
        args.write_candidate.write_text(
            json.dumps(cand_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    doc = {
        "schema": "market_psych_manifest_holdout_sweep_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "a_track_autotrigger_forbidden": True,
        "split": {
            "holdout_days": args.holdout_days,
            "train_dates": len(train),
            "holdout_dates": len(holdout),
            "holdout_range": [holdout[0], holdout[-1]] if holdout else [],
            "train_range": [train[0], train[-1]] if train else [],
        },
        "inputs": {
            "psych_csv": str(args.psych_csv.resolve()),
            "kospi_csv": str(args.kospi_csv.resolve()),
            "base_manifest": str(args.base_manifest.resolve()),
            "neutral_bps": args.neutral_bps,
        },
        "candidate_count": len(rows),
        "ranking_by_train_kospi": rows,
        "best_on_train": best,
        "baseline": baseline_row,
        "candidate_manifest_path": str(args.write_candidate.resolve()) if winner_spec else None,
        "verdict_ko": _verdict_ko(best),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/market_psych_manifest_holdout_sweep_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
