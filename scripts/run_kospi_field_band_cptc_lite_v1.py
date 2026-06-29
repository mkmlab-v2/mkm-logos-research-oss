#!/usr/bin/env python3
"""CPTC-lite: change-point segmented online conformal band margin [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_kospi_field_band_rwc_lite_v1 import (  # noqa: E402
    _outside_distance_pct,
    _weighted_quantile,
)
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
    _has_conflict_surface,
    _rolling_vol_pct,
    _scored_rows,
)
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import _soft_score  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_cptc_lite_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_cptc_lite_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_field_band_cptc_lite_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vol_jump_ratio(
    row: dict[str, Any],
    *,
    ret_hist_by_date: dict[str, float],
    dates_sorted: list[str],
    vol_window: int,
) -> float | None:
    vol_now = _rolling_vol_pct(row, ret_hist_by_date=ret_hist_by_date, dates_sorted=dates_sorted, vol_window=vol_window)
    if vol_now is None or vol_now <= 0:
        return None
    dk = str(row.get("session_date"))
    try:
        idx = dates_sorted.index(dk)
    except ValueError:
        return None
    if idx < vol_window:
        return None
    prior_dates = dates_sorted[max(0, idx - vol_window) : idx]
    prior_vols = []
    for pd in prior_dates:
        fake_row = {"session_date": pd}
        v = _rolling_vol_pct(fake_row, ret_hist_by_date=ret_hist_by_date, dates_sorted=dates_sorted, vol_window=vol_window)
        if v is not None and v > 0:
            prior_vols.append(v)
    if not prior_vols:
        return None
    prior_mean = sum(prior_vols) / len(prior_vols)
    if prior_mean <= 0:
        return None
    return vol_now / prior_mean


def _is_change_point(
    *,
    shock_day: bool,
    prev_shock: bool,
    vol_jump: float | None,
    vol_jump_threshold: float,
    conflict: bool,
    prev_conflict: bool,
) -> bool:
    if shock_day and not prev_shock:
        return True
    if vol_jump is not None and vol_jump >= vol_jump_threshold:
        return True
    if conflict and not prev_conflict:
        return True
    return False


def run_cptc_lite(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    n_folds: int = 4,
    target_coverage: float = 0.9,
    coverage_gap: float = 0.05,
    base_quantile_q: float = 0.88,
    quantile_step: float = 0.03,
    max_quantile_q: float = 0.97,
    vol_jump_threshold: float = 1.75,
    margin_gamma: float = 0.18,
    max_extra_scale: float = 2.5,
    min_segment_n: int = 3,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    cal_by_date = _calendar_rows(calendar)
    ret_hist = {str(r["session_date"]): float(r.get("daily_return_pct") or 0.0) / 100.0 for r in rows}
    policy = _policy_from_tier2(field_tier2)
    holdout = _holdout_dates(dates, n_folds)
    conflict = _has_conflict_surface(fusion)

    segment_ncs: list[float] = []
    segment_hits: list[bool] = []
    segment_id = 0
    adaptive_q = base_quantile_q
    prev_shock = False
    prev_conflict = conflict
    change_points = 0
    daily: list[dict[str, Any]] = []

    for row in rows:
        dk = str(row.get("session_date"))
        scale, shock_day, _vol_pct = _compute_band_scale(
            row,
            fusion,
            policy=policy,
            ret_hist_by_date=ret_hist,
            dates_sorted=dates,
        )
        vol_jump = _vol_jump_ratio(
            row,
            ret_hist_by_date=ret_hist,
            dates_sorted=dates,
            vol_window=int(policy["vol_window"]),
        )
        cp = _is_change_point(
            shock_day=shock_day,
            prev_shock=prev_shock,
            vol_jump=vol_jump,
            vol_jump_threshold=vol_jump_threshold,
            conflict=conflict,
            prev_conflict=prev_conflict,
        )
        if cp and (segment_ncs or segment_hits):
            segment_id += 1
            segment_ncs = []
            segment_hits = []
            adaptive_q = base_quantile_q
            change_points += 1

        cal_row = cal_by_date.get(dk)
        base_hit = _band_hit(row, cal_row, band_scale=scale)

        if len(segment_ncs) >= min_segment_n:
            c_t = _weighted_quantile(segment_ncs, [1.0] * len(segment_ncs), adaptive_q)
        elif segment_ncs:
            c_t = max(segment_ncs)
        else:
            c_t = 0.0

        extra = min(max_extra_scale, margin_gamma * c_t)
        cptc_scale = scale * (1.0 + extra)
        cptc_hit = _band_hit(row, cal_row, band_scale=cptc_scale)
        nc = _outside_distance_pct(row, cal_row, band_scale=scale)

        seg_cov = (sum(1 for h in segment_hits if h) / len(segment_hits)) if segment_hits else None
        daily.append(
            {
                "session_date": dk,
                "arm_id": ARM_ID,
                "segment_id": segment_id,
                "change_point": cp,
                "band_scale_base": round(scale, 4),
                "cptc_margin_pct": round(c_t, 4),
                "cptc_extra_scale_factor": round(extra, 4),
                "band_scale_cptc": round(cptc_scale, 4),
                "band_hit_base": base_hit,
                "band_hit_cptc": cptc_hit,
                "nonconformity_pct": round(nc, 4),
                "segment_coverage_prior": round(seg_cov, 4) if seg_cov is not None else None,
                "adaptive_quantile_q": round(adaptive_q, 4),
                "vol_jump_ratio": round(vol_jump, 4) if vol_jump is not None else None,
                "shock_day": shock_day,
                "holdout_fold_day": dk in holdout,
                "predicted_direction": row.get("predicted_direction"),
                "actual_direction": row.get("actual_direction"),
            }
        )

        segment_ncs.append(nc)
        if isinstance(base_hit, bool):
            segment_hits.append(base_hit)
            if len(segment_hits) >= min_segment_n:
                cov = sum(1 for h in segment_hits if h) / len(segment_hits)
                if cov < target_coverage - coverage_gap:
                    adaptive_q = min(max_quantile_q, adaptive_q + quantile_step)

        prev_shock = shock_day
        prev_conflict = conflict

    def _summarize(sub: list[dict[str, Any]]) -> dict[str, Any]:
        if not sub:
            return {"n_scored": 0, "band_hit_rate_base": None, "band_hit_rate_cptc": None}
        base_hits = [r["band_hit_base"] for r in sub]
        cptc_hits = [r["band_hit_cptc"] for r in sub]
        return {
            "n_scored": len(sub),
            "band_hit_rate_base": _band_hit_rate([h if isinstance(h, bool) else None for h in base_hits]),
            "band_hit_rate_cptc": _band_hit_rate([h if isinstance(h, bool) else None for h in cptc_hits]),
            "mean_cptc_extra_scale": round(
                sum(float(r.get("cptc_extra_scale_factor") or 0.0) for r in sub) / len(sub), 4
            ),
        }

    full = _summarize(daily)
    hold = _summarize([r for r in daily if r.get("holdout_fold_day")])
    delta = round(float(hold.get("band_hit_rate_cptc") or 0.0) - float(hold.get("band_hit_rate_base") or 0.0), 4)

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
        "schema": "kospi_field_band_cptc_lite_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "arm_id": ARM_ID,
        "layer": "field_band_change_point_conformal",
        "direction_unchanged": True,
        "policy": {
            "target_coverage": target_coverage,
            "coverage_gap": coverage_gap,
            "base_quantile_q": base_quantile_q,
            "vol_jump_threshold": vol_jump_threshold,
            "margin_gamma": margin_gamma,
            "max_extra_scale": max_extra_scale,
            "min_segment_n": min_segment_n,
        },
        "n_scored_total": len(daily),
        "change_point_count": change_points,
        "daily_rows": daily,
        "summary": {
            "full_window": full,
            "holdout_pooled": hold,
            "delta_cptc_minus_base_holdout": delta,
            "direction_soft_hit_rate_holdout": _soft_score(hold_dir),
        },
        "promotion_candidate": promotion_candidate,
        "verdict_ko": (
            "CPTC-lite holdout band coverage 개선 — 연구 후보"
            if promotion_candidate
            else "CPTC-lite holdout 개선 미달 — vol-widen baseline 유지"
        ),
        "pointers": {
            "eval": "reports/kospi_multi_month_prophecy_eval_v1_latest.json",
            "rwc_lite": "reports/kospi_field_band_rwc_lite_v1_latest.json",
            "tier0": "docs/research/raw/KOSPI_SHOCK_CONDITIONAL_FUSION_FAILURE_RECOVERY_TIER0_2026-06-23.md",
        },
        "reproduce": "py scripts/run_kospi_field_band_hd_auto_chain_v1.py",
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

    doc = run_cptc_lite(
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
                "holdout_cptc": hold.get("band_hit_rate_cptc"),
                "delta": (doc.get("summary") or {}).get("delta_cptc_minus_base_holdout"),
                "change_points": doc.get("change_point_count"),
                "promotion_candidate": doc.get("promotion_candidate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
