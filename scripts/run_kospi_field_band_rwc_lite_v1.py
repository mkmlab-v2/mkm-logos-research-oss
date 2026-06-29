#!/usr/bin/env python3
"""RWC-lite: regime-weighted conformal margin on Field band layer [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_kospi_field_band_shadow_replay_v1 import (  # noqa: E402
    ARM_ID,
    _compute_band_scale,
    _holdout_dates,
    _policy_from_tier2,
)
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import (  # noqa: E402
    _band_hit,
    _band_hit_rate,
    _calendar_rows,
    _scored_rows,
)
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import _soft_score  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_rwc_lite_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_field_band_rwc_lite_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _regime_vec(*, shock_day: bool, vol_pct: float | None, conflict: bool, band_scale: float) -> list[float]:
    return [
        1.0 if shock_day else 0.0,
        float(vol_pct or 0.0) * 100.0,
        1.0 if conflict else 0.0,
        min(float(band_scale), 12.0) / 12.0,
    ]


def _sq_dist(a: list[float], b: list[float]) -> float:
    return sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))


def _regime_weights(
    past: list[dict[str, Any]],
    z_t: list[float],
    *,
    decay_lambda: float,
    bandwidth_h: float,
    idx_t: int,
) -> list[float]:
    weights: list[float] = []
    for j, rec in enumerate(past):
        age = idx_t - j
        if age <= 0:
            weights.append(0.0)
            continue
        time_w = math.exp(-decay_lambda * age)
        z_j = rec["regime_vec"]
        kernel = math.exp(-_sq_dist(z_j, z_t) / (2.0 * bandwidth_h**2))
        weights.append(time_w * kernel)
    return weights


def _n_eff(weights: list[float]) -> float:
    ws = [w for w in weights if w > 0]
    if not ws:
        return 0.0
    s = sum(ws)
    s2 = sum(w * w for w in ws)
    return (s * s) / s2 if s2 > 0 else 0.0


def _weighted_quantile(values: list[float], weights: list[float], q: float) -> float:
    pairs = [(v, w) for v, w in zip(values, weights) if w > 0 and v >= 0]
    if not pairs:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        return 0.0
    target = q * total
    cum = 0.0
    for v, w in pairs:
        cum += w
        if cum >= target:
            return float(v)
    return float(pairs[-1][0])


def _outside_distance_pct(
    row: dict[str, Any],
    cal_row: dict[str, Any] | None,
    *,
    band_scale: float,
) -> float:
    """Nonconformity: distance outside symmetric return band (%), 0 if inside."""
    prior = row.get("prior_close")
    close = row.get("actual_close")
    if prior is None or close is None:
        return 0.0
    try:
        prior_f = float(prior)
        close_f = float(close)
    except (TypeError, ValueError):
        return 0.0
    if prior_f <= 0:
        return 0.0
    band = (cal_row or {}).get("kospi_index_prophecy") if isinstance(cal_row, dict) else {}
    if not isinstance(band, dict):
        band = {}
    band_pct = band.get("predicted_return_band_pct") or [None, None]
    if band_pct[0] is None or band_pct[1] is None:
        return 0.0
    lo_pct = float(band_pct[0]) * band_scale
    hi_pct = float(band_pct[1]) * band_scale
    ret_pct = (close_f / prior_f - 1.0) * 100.0
    if lo_pct <= ret_pct <= hi_pct:
        return 0.0
    if ret_pct < lo_pct:
        return lo_pct - ret_pct
    return ret_pct - hi_pct


def run_rwc_lite(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    n_folds: int = 4,
    decay_lambda: float = 0.05,
    bandwidth_h: float = 1.0,
    quantile_q: float = 0.9,
    n_min_eff: float = 8.0,
    margin_gamma: float = 0.15,
    max_extra_scale: float = 2.0,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    cal_by_date = _calendar_rows(calendar)
    ret_hist = {str(r["session_date"]): float(r.get("daily_return_pct") or 0.0) / 100.0 for r in rows}
    policy = _policy_from_tier2(field_tier2)
    holdout = _holdout_dates(dates, n_folds)
    conflict = bool((fusion.get("fusion_resolution") or {}).get("conflict_ids"))

    history: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        dk = str(row.get("session_date"))
        scale, shock_day, vol_pct = _compute_band_scale(
            row,
            fusion,
            policy=policy,
            ret_hist_by_date=ret_hist,
            dates_sorted=dates,
        )
        z_t = _regime_vec(shock_day=shock_day, vol_pct=vol_pct, conflict=conflict, band_scale=scale)
        nc_hist = [float(h["nonconformity_pct"]) for h in history]
        w = _regime_weights(history, z_t, decay_lambda=decay_lambda, bandwidth_h=bandwidth_h, idx_t=idx)
        n_eff = _n_eff(w)
        if n_eff < n_min_eff and history:
            w = [math.exp(-decay_lambda * (idx - j)) if j < idx else 0.0 for j in range(len(history))]
            n_eff = _n_eff(w)
            fallback = "time_decay_only"
        else:
            fallback = None

        c_t = _weighted_quantile(nc_hist, w, quantile_q) if history else 0.0
        extra = min(max_extra_scale, margin_gamma * c_t)
        rwc_scale = scale * (1.0 + extra)

        cal_row = cal_by_date.get(dk)
        base_hit = _band_hit(row, cal_row, band_scale=scale)
        rwc_hit = _band_hit(row, cal_row, band_scale=rwc_scale)
        nc = _outside_distance_pct(row, cal_row, band_scale=scale)

        entry = {
            "session_date": dk,
            "arm_id": ARM_ID,
            "band_scale_base": round(scale, 4),
            "rwc_margin_pct": round(c_t, 4),
            "rwc_extra_scale_factor": round(extra, 4),
            "band_scale_rwc": round(rwc_scale, 4),
            "band_hit_base": base_hit,
            "band_hit_rwc": rwc_hit,
            "nonconformity_pct": round(nc, 4),
            "n_eff": round(n_eff, 2),
            "regime_fallback": fallback,
            "shock_day": shock_day,
            "holdout_fold_day": dk in holdout,
            "predicted_direction": row.get("predicted_direction"),
            "actual_direction": row.get("actual_direction"),
        }
        daily.append(entry)
        history.append({"regime_vec": z_t, "nonconformity_pct": nc})

    def _summarize(sub: list[dict[str, Any]]) -> dict[str, Any]:
        if not sub:
            return {"n_scored": 0, "band_hit_rate_base": None, "band_hit_rate_rwc": None}
        base_hits = [r["band_hit_base"] for r in sub]
        rwc_hits = [r["band_hit_rwc"] for r in sub]
        return {
            "n_scored": len(sub),
            "band_hit_rate_base": _band_hit_rate([h if isinstance(h, bool) else None for h in base_hits]),
            "band_hit_rate_rwc": _band_hit_rate([h if isinstance(h, bool) else None for h in rwc_hits]),
            "mean_rwc_extra_scale": round(
                sum(float(r.get("rwc_extra_scale_factor") or 0.0) for r in sub) / len(sub), 4
            ),
        }

    full = _summarize(daily)
    hold = _summarize([r for r in daily if r.get("holdout_fold_day")])
    base_rate = float(hold.get("band_hit_rate_base") or 0.0)
    rwc_rate = float(hold.get("band_hit_rate_rwc") or 0.0)
    delta = round(rwc_rate - base_rate, 4)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome

    hold_dir = [
        _outcome(p, a)
        for p, a in zip(
            [r.get("predicted_direction") for r in daily if r.get("holdout_fold_day")],
            [r.get("actual_direction") for r in daily if r.get("holdout_fold_day")],
        )
    ]

    promotion_candidate = delta >= 0.03 and int(hold.get("n_scored") or 0) >= 30

    return {
        "schema": "kospi_field_band_rwc_lite_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "arm_id": ARM_ID,
        "layer": "field_band_post_hoc_conformal",
        "direction_unchanged": True,
        "policy": {
            "decay_lambda": decay_lambda,
            "bandwidth_h": bandwidth_h,
            "quantile_q": quantile_q,
            "n_min_eff": n_min_eff,
            "margin_gamma": margin_gamma,
            "max_extra_scale": max_extra_scale,
        },
        "n_scored_total": len(daily),
        "daily_rows": daily,
        "summary": {
            "full_window": full,
            "holdout_pooled": hold,
            "delta_rwc_minus_base_holdout": delta,
            "direction_soft_hit_rate_holdout": _soft_score(hold_dir),
        },
        "promotion_candidate": promotion_candidate,
        "verdict_ko": (
            "RWC-lite holdout band coverage 개선 — 연구 후보"
            if promotion_candidate
            else "RWC-lite holdout 개선 미달 — vol-widen baseline 유지"
        ),
        "pointers": {
            "eval": "reports/kospi_multi_month_prophecy_eval_v1_latest.json",
            "calendar": "reports/kospi_multi_month_prophecy_calendar_v1_latest.json",
            "tier0": "docs/research/raw/KOSPI_SHOCK_CONDITIONAL_FUSION_FAILURE_RECOVERY_TIER0_2026-06-23.md",
        },
        "reproduce": "py scripts/run_kospi_field_band_rwc_lite_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not ev or not cal or not fusion:
        print("Missing eval, calendar, or fusion", file=sys.stderr)
        return 2

    doc = run_rwc_lite(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        n_folds=args.n_folds,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in doc.get("daily_rows") or []:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    hold = (doc.get("summary") or {}).get("holdout_pooled") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "holdout_base": hold.get("band_hit_rate_base"),
                "holdout_rwc": hold.get("band_hit_rate_rwc"),
                "delta": (doc.get("summary") or {}).get("delta_rwc_minus_base_holdout"),
                "promotion_candidate": doc.get("promotion_candidate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
