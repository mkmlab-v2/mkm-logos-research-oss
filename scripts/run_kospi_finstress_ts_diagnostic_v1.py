#!/usr/bin/env python3
"""FinStressTS-lite: shock-fusion failure diagnostic sandbox [HYPO][B-track]."""
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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.run_kospi_field_band_shadow_replay_v1 import _holdout_dates  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import (  # noqa: E402
    _fusion_adjusted_direction,
    _read,
)
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import (  # noqa: E402
    _has_conflict_surface,
    _rolling_vol_pct,
    _scored_rows,
)
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import (  # noqa: E402
    PRIOR_SHOCK_PCT,
    SHOCK_RETURN_PCT,
    _is_shock_day,
    _soft_score,
)
from scripts.run_kospi_four_lens_shock_fusion_walkforward_v1 import _predict_for_row  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_SHOCK_WF = ROOT / "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_finstress_ts_diagnostic_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_finstress_ts_diagnostic_v1_latest.json"

ARM_IDS = ("active", "fusion_always", "fusion_shock_only")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _arm_soft_hit(
    rows: list[dict[str, Any]],
    fusion: dict[str, Any],
    *,
    mode: str,
) -> float:
    outcomes: list[str] = []
    for row in rows:
        actual = row.get("actual_direction")
        if actual not in ("bull", "bear", "neutral"):
            continue
        pred = _predict_for_row(
            row,
            fusion,
            mode=mode,
            shock_return_pct=SHOCK_RETURN_PCT,
            prior_shock_pct=PRIOR_SHOCK_PCT,
        )
        outcomes.append(_outcome(pred, str(actual)))
    return _soft_score(outcomes)


def _mean_abs(xs: list[float]) -> float | None:
    if not xs:
        return None
    return round(sum(xs) / len(xs), 4)


def run_finstress_diagnostic(
    eval_doc: dict[str, Any],
    fusion: dict[str, Any],
    *,
    shock_wf: dict[str, Any] | None = None,
    n_folds: int = 4,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    holdout = _holdout_dates(dates, n_folds)
    ret_hist = {str(r["session_date"]): float(r.get("daily_return_pct") or 0.0) / 100.0 for r in rows}
    conflict = _has_conflict_surface(fusion)

    hold_rows = [r for r in rows if str(r.get("session_date")) in holdout]
    shock_rows = [r for r in hold_rows if _is_shock_day(r, shock_return_pct=SHOCK_RETURN_PCT, prior_shock_pct=PRIOR_SHOCK_PCT)]
    calm_rows = [r for r in hold_rows if r not in shock_rows]

    flip_count = 0
    flip_on_calm = 0
    stress_feats: list[dict[str, Any]] = []
    for row in hold_rows:
        pred_active = str(row.get("predicted_direction"))
        pred_fusion = _fusion_adjusted_direction(fusion, pred_active)
        shock = _is_shock_day(row, shock_return_pct=SHOCK_RETURN_PCT, prior_shock_pct=PRIOR_SHOCK_PCT)
        flipped = pred_fusion != pred_active
        if flipped:
            flip_count += 1
            if not shock:
                flip_on_calm += 1
        vol = _rolling_vol_pct(row, ret_hist_by_date=ret_hist, dates_sorted=dates, vol_window=5)
        stress_feats.append(
            {
                "session_date": row.get("session_date"),
                "shock_day": shock,
                "abs_return_pct": round(abs(float(row.get("daily_return_pct") or 0.0)), 4),
                "rolling_vol_pct": round(vol, 6) if vol is not None else None,
                "direction_flip": flipped,
                "backfill_source": row.get("backfill_source"),
            }
        )

    abs_shock = [f["abs_return_pct"] for f in stress_feats if f["shock_day"]]
    abs_calm = [f["abs_return_pct"] for f in stress_feats if not f["shock_day"]]
    vol_shock = [f["rolling_vol_pct"] for f in stress_feats if f["shock_day"] and f["rolling_vol_pct"] is not None]
    vol_calm = [f["rolling_vol_pct"] for f in stress_feats if not f["shock_day"] and f["rolling_vol_pct"] is not None]

    arms_holdout = {arm: _arm_soft_hit(hold_rows, fusion, mode=arm) for arm in ARM_IDS}
    arms_shock = {arm: _arm_soft_hit(shock_rows, fusion, mode=arm) for arm in ARM_IDS}
    arms_calm = {arm: _arm_soft_hit(calm_rows, fusion, mode=arm) for arm in ARM_IDS}

    june_wf = shock_wf or {}
    june_delta = ((june_wf.get("comparison") or {}).get("delta_shock_only_minus_active_holdout"))
    fusion_always_june = (
        ((june_wf.get("holdout_pooled") or {}).get("fusion_always") or {}).get("soft_hit_rate")
    )

    root_causes: list[str] = []
    if flip_on_calm > 0 and arms_calm.get("fusion_always", 1.0) < arms_calm.get("active", 1.0):
        root_causes.append("early_fusion_direction_flip_on_calm_days")
    if arms_shock.get("fusion_shock_only", 0) >= arms_shock.get("active", 0) and arms_calm.get("fusion_always", 0) < arms_calm.get("active", 0):
        root_causes.append("shock_only_ok_but_always_on_hurts_calm")
    if conflict and flip_count > len(hold_rows) * 0.2:
        root_causes.append("conflict_surface_drives_excess_flips")
    if not root_causes:
        root_causes.append("insufficient_separation_in_holdout_panel")

    recommendation = (
        "late_condition_band_only_no_direction_fusion"
        if "early_fusion_direction_flip_on_calm_days" in root_causes
        or "shock_only_ok_but_always_on_hurts_calm" in root_causes
        else "collect_more_prophecy_band_days_before_fusion_retry"
    )

    return {
        "schema": "kospi_finstress_ts_diagnostic_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "promotion_candidate": False,
        "diagnostic_only": True,
        "holdout_n": len(hold_rows),
        "shock_days_holdout": len(shock_rows),
        "calm_days_holdout": len(calm_rows),
        "direction_flip_rate_holdout": round(flip_count / len(hold_rows), 4) if hold_rows else None,
        "direction_flip_on_calm_days": flip_on_calm,
        "conflict_surface": conflict,
        "stress_features": {
            "mean_abs_return_shock": _mean_abs(abs_shock),
            "mean_abs_return_calm": _mean_abs(abs_calm),
            "mean_vol_shock": _mean_abs(vol_shock) if vol_shock else None,
            "mean_vol_calm": _mean_abs(vol_calm) if vol_calm else None,
            "vol_ratio_shock_over_calm": (
                round(_mean_abs(vol_shock) / _mean_abs(vol_calm), 4)  # type: ignore[operator]
                if vol_shock and vol_calm and _mean_abs(vol_calm)
                else None
            ),
        },
        "direction_soft_hit_holdout": arms_holdout,
        "direction_soft_hit_shock_subset": arms_shock,
        "direction_soft_hit_calm_subset": arms_calm,
        "june_walkforward_anchor": {
            "delta_shock_only_minus_active_holdout_pp": june_delta,
            "fusion_always_holdout_soft_hit_june": fusion_always_june,
        },
        "root_cause_tags": root_causes,
        "recommendation": recommendation,
        "verdict_ko": (
            "충격일 조건부는 유지 가능·always-on 방향 융합은 평온일 손실 — 밴드 late conditioning 유지"
            if recommendation == "late_condition_band_only_no_direction_fusion"
            else "추가 prophecy 밴드 일수 확보 후 재평가"
        ),
        "daily_stress_rows": stress_feats,
        "pointers": {
            "eval": "reports/kospi_multi_month_prophecy_eval_v1_latest.json",
            "shock_wf": "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.json",
            "tier0": "docs/research/raw/KOSPI_SHOCK_CONDITIONAL_FUSION_FAILURE_RECOVERY_TIER0_2026-06-23.md",
        },
        "reproduce": "py scripts/run_kospi_finstress_ts_diagnostic_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--shock-wf-json", type=Path, default=DEFAULT_SHOCK_WF)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    fusion = _read(args.fusion_json)
    if not ev or not fusion:
        print("Missing eval or fusion", file=sys.stderr)
        return 2

    doc = run_finstress_diagnostic(
        ev,
        fusion,
        shock_wf=_read(args.shock_wf_json),
        n_folds=args.n_folds,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "recommendation": doc.get("recommendation"),
                "root_causes": doc.get("root_cause_tags"),
                "holdout_direction": doc.get("direction_soft_hit_holdout"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
