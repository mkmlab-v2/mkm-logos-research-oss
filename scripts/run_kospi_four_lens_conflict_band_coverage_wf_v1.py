#!/usr/bin/env python3
"""Conflict/shock band-widen walk-forward (coverage-first, direction unchanged) [HYPO]."""
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
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import (  # noqa: E402
    PRIOR_SHOCK_PCT,
    SHOCK_RETURN_PCT,
    _is_shock_day,
    _soft_score,
)
from scripts.run_kospi_four_lens_shock_fusion_walkforward_v1 import blocked_folds  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
DEFAULT_MD = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.md"

ARM_IDS = ("band_active", "band_shock_widen", "band_conflict_shock_widen")
DEFAULT_SHOCK_SCALE = 1.5
DEFAULT_CONFLICT_SHOCK_SCALE = 1.75
DEFAULT_VOL_BAND_K = 1.5
DEFAULT_VOL_WINDOW = 5


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scored_rows(eval_doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = eval_doc.get("rows")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("actual_direction") not in ("bull", "bear", "neutral"):
            continue
        out.append(row)
    out.sort(key=lambda r: str(r.get("session_date") or ""))
    return out


def _calendar_rows(calendar: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = calendar.get("rows")
    if not isinstance(rows, list):
        return {}
    return {str(r.get("session_date")): r for r in rows if isinstance(r, dict) and r.get("session_date")}


def _has_conflict_surface(fusion: dict[str, Any]) -> bool:
    res = fusion.get("fusion_resolution") or {}
    conflicts = res.get("conflict_ids") or []
    return bool(conflicts)


def _band_scale_for_mode(
    *,
    mode: str,
    row: dict[str, Any],
    fusion: dict[str, Any],
    shock_return_pct: float,
    prior_shock_pct: float,
    shock_scale: float,
    conflict_shock_scale: float,
) -> float:
    if mode == "band_active":
        return 1.0
    shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
    if not shock:
        return 1.0
    if mode == "band_shock_widen":
        return shock_scale
    if mode == "band_conflict_shock_widen":
        return conflict_shock_scale if _has_conflict_surface(fusion) else 1.0
    return 1.0


def _rolling_vol_pct(
    row: dict[str, Any],
    *,
    ret_hist_by_date: dict[str, float],
    dates_sorted: list[str],
    vol_window: int,
) -> float | None:
    if vol_window < 2:
        return None
    dk = str(row.get("session_date") or "")
    if not dk:
        return None
    try:
        idx = dates_sorted.index(dk)
    except ValueError:
        return None
    prior = [dates_sorted[i] for i in range(max(0, idx - vol_window), idx)]
    vals = [ret_hist_by_date[d] for d in prior if d in ret_hist_by_date]
    if len(vals) < 2:
        return None
    import statistics

    return abs(float(statistics.pstdev(vals)))


def _band_hit(
    row: dict[str, Any],
    cal_row: dict[str, Any] | None,
    *,
    band_scale: float,
) -> bool | None:
    prior = row.get("prior_close")
    close = row.get("actual_close")
    if prior is None or close is None:
        return row.get("band_hit")
    try:
        prior_f = float(prior)
        close_f = float(close)
    except (TypeError, ValueError):
        return row.get("band_hit")
    if prior_f <= 0:
        return row.get("band_hit")

    band = (cal_row or {}).get("kospi_index_prophecy") if isinstance(cal_row, dict) else {}
    if not isinstance(band, dict):
        band = {}
    band_pct = band.get("predicted_return_band_pct") or [None, None]
    if band_pct[0] is not None and band_pct[1] is not None:
        lo_pct = float(band_pct[0]) * band_scale
        hi_pct = float(band_pct[1]) * band_scale
        lo_close = prior_f * (1.0 + lo_pct / 100.0)
        hi_close = prior_f * (1.0 + hi_pct / 100.0)
        return float(min(lo_close, hi_close)) <= close_f <= float(max(lo_close, hi_close))

    lo, hi = band.get("predicted_close_band") or [None, None]
    if lo is not None and hi is not None:
        lo_f, hi_f = float(lo), float(hi)
        mid = (lo_f + hi_f) / 2.0
        half = abs(hi_f - lo_f) / 2.0 * band_scale
        return mid - half <= close_f <= mid + half
    return row.get("band_hit")


def _band_hit_rate(hits: list[bool | None]) -> float | None:
    scored = [h for h in hits if h is not None]
    if not scored:
        return None
    return round(sum(1 for h in scored if h) / len(scored), 4)


def _score_rows(
    rows: list[dict[str, Any]],
    cal_by_date: dict[str, dict[str, Any]],
    fusion: dict[str, Any],
    *,
    mode: str,
    shock_return_pct: float,
    prior_shock_pct: float,
    shock_scale: float,
    conflict_shock_scale: float,
    vol_band_k: float,
    vol_window: int,
    ret_hist_by_date: dict[str, float],
    dates_sorted: list[str],
) -> dict[str, Any]:
    band_hits: list[bool | None] = []
    dir_outcomes: list[str] = []
    widened_days = 0
    for row in rows:
        scale = _band_scale_for_mode(
            mode=mode,
            row=row,
            fusion=fusion,
            shock_return_pct=shock_return_pct,
            prior_shock_pct=prior_shock_pct,
            shock_scale=shock_scale,
            conflict_shock_scale=conflict_shock_scale,
        )
        if mode == "band_conflict_vol_widen":
            shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
            if shock and _has_conflict_surface(fusion):
                vol = _rolling_vol_pct(
                    row,
                    ret_hist_by_date=ret_hist_by_date,
                    dates_sorted=dates_sorted,
                    vol_window=vol_window,
                )
                if vol is not None:
                    scale = max(1.0, vol_band_k * (vol / 0.01))
        if scale > 1.0:
            widened_days += 1
        dk = str(row.get("session_date"))
        hit = _band_hit(row, cal_by_date.get(dk), band_scale=scale)
        band_hits.append(hit)
        pred = str(row.get("predicted_direction"))
        actual = str(row.get("actual_direction"))
        dir_outcomes.append(_outcome(pred, actual))
    return {
        "n_scored": len(rows),
        "widened_days": widened_days,
        "band_hit_rate": _band_hit_rate(band_hits),
        "direction_soft_hit_rate": _soft_score(dir_outcomes),
    }


def run_conflict_band_coverage_wf(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    n_folds: int = 4,
    shock_return_pct: float = SHOCK_RETURN_PCT,
    prior_shock_pct: float = PRIOR_SHOCK_PCT,
    shock_scale: float = DEFAULT_SHOCK_SCALE,
    conflict_shock_scale: float = DEFAULT_CONFLICT_SHOCK_SCALE,
    vol_band_k: float = DEFAULT_VOL_BAND_K,
    vol_window: int = DEFAULT_VOL_WINDOW,
    min_holdout_n: int = 10,
    min_delta_pp: float = 0.03,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    row_by_date = {str(r["session_date"]): r for r in rows}
    ret_hist_by_date = {str(r["session_date"]): float(r.get("daily_return_pct") or 0.0) / 100.0 for r in rows}
    cal_by_date = _calendar_rows(calendar)
    folds = blocked_folds(dates, n_folds)
    arm_ids = ARM_IDS + ("band_conflict_vol_widen",)

    holdout_band_hits: dict[str, list[bool | None]] = {aid: [] for aid in arm_ids}
    holdout_dir_outcomes: dict[str, list[str]] = {aid: [] for aid in arm_ids}
    fold_docs: list[dict[str, Any]] = []

    for fi, (train, test) in enumerate(folds):
        test_rows = [row_by_date[d] for d in test]
        arms: dict[str, Any] = {}
        for mode in arm_ids:
            summary = _score_rows(
                test_rows,
                cal_by_date,
                fusion,
                mode=mode,
                shock_return_pct=shock_return_pct,
                prior_shock_pct=prior_shock_pct,
                shock_scale=shock_scale,
                conflict_shock_scale=conflict_shock_scale,
                vol_band_k=vol_band_k,
                vol_window=vol_window,
                ret_hist_by_date=ret_hist_by_date,
                dates_sorted=dates,
            )
            arms[mode] = summary
            for row in test_rows:
                scale = _band_scale_for_mode(
                    mode=mode,
                    row=row,
                    fusion=fusion,
                    shock_return_pct=shock_return_pct,
                    prior_shock_pct=prior_shock_pct,
                    shock_scale=shock_scale,
                    conflict_shock_scale=conflict_shock_scale,
                )
                if mode == "band_conflict_vol_widen":
                    shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
                    if shock and _has_conflict_surface(fusion):
                        vol = _rolling_vol_pct(
                            row,
                            ret_hist_by_date=ret_hist_by_date,
                            dates_sorted=dates,
                            vol_window=vol_window,
                        )
                        if vol is not None:
                            scale = max(1.0, vol_band_k * (vol / 0.01))
                dk = str(row.get("session_date"))
                holdout_band_hits[mode].append(_band_hit(row, cal_by_date.get(dk), band_scale=scale))
                holdout_dir_outcomes[mode].append(
                    _outcome(str(row.get("predicted_direction")), str(row.get("actual_direction")))
                )
        fold_docs.append(
            {
                "fold": fi,
                "protocol": "blocked_expanding_train_test_only",
                "train_window": {"date_from": train[0], "date_to": train[-1], "n_days": len(train)},
                "test_window": {"date_from": test[0], "date_to": test[-1], "n_days": len(test)},
                "arms": arms,
            }
        )

    holdout_pooled: dict[str, Any] = {}
    for mode in arm_ids:
        holdout_pooled[mode] = {
            "n_scored": len(holdout_band_hits[mode]),
            "band_hit_rate": _band_hit_rate(holdout_band_hits[mode]),
            "direction_soft_hit_rate": _soft_score(holdout_dir_outcomes[mode]),
        }

    active_band = float(holdout_pooled["band_active"]["band_hit_rate"] or 0.0)
    shock_band = float(holdout_pooled["band_shock_widen"]["band_hit_rate"] or 0.0)
    conflict_band = float(holdout_pooled["band_conflict_shock_widen"]["band_hit_rate"] or 0.0)
    conflict_vol_band = float(holdout_pooled["band_conflict_vol_widen"]["band_hit_rate"] or 0.0)
    n_holdout = int(holdout_pooled["band_active"]["n_scored"])
    delta_shock = round(shock_band - active_band, 4)
    delta_conflict = round(conflict_band - active_band, 4)
    delta_conflict_vol = round(conflict_vol_band - active_band, 4)
    promotion_ready = delta_conflict_vol >= min_delta_pp and n_holdout >= min_holdout_n

    return {
        "schema": "kospi_four_lens_conflict_band_coverage_wf_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "metric_primary": "band_hit_rate",
        "metric_secondary": "direction_soft_hit_rate",
        "eval_pointer": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        "calendar_pointer": "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        "fusion_pointer": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
        "band_policy": {
            "shock_scale": shock_scale,
            "conflict_shock_scale": conflict_shock_scale,
            "vol_band_k": vol_band_k,
            "vol_window": vol_window,
            "direction_unchanged": True,
        },
        "shock_thresholds": {
            "abs_return_pct": shock_return_pct,
            "prior_kospi_pct": prior_shock_pct,
        },
        "config": {
            "n_folds": n_folds,
            "protocol": "blocked_expanding_train_test_only",
            "min_holdout_n": min_holdout_n,
            "min_delta_pp": min_delta_pp,
        },
        "n_scored_total": len(rows),
        "folds": fold_docs,
        "holdout_pooled": holdout_pooled,
        "comparison": {
            "delta_shock_widen_minus_active_band_holdout": delta_shock,
            "delta_conflict_shock_widen_minus_active_band_holdout": delta_conflict,
            "delta_conflict_vol_widen_minus_active_band_holdout": delta_conflict_vol,
            "conflict_widen_beats_shock_widen_holdout": conflict_band > shock_band,
            "conflict_vol_widen_beats_conflict_widen_holdout": conflict_vol_band > conflict_band,
        },
        "promotion_ready": promotion_ready,
        "verdict_ko": (
            "holdout band coverage +3%p — conflict vol-widen 연구 후보"
            if promotion_ready
            else "band widen도 holdout 승격 미달 — coverage 리포트만 유지"
        ),
    }


def render_md(doc: dict[str, Any]) -> str:
    hold = doc.get("holdout_pooled") or {}
    cmp_ = doc.get("comparison") or {}
    pol = doc.get("band_policy") or {}
    lines = [
        "> **[HYPO][research_only]** conflict/shock band-widen WF (direction unchanged).",
        "",
        f"- primary metric: `{doc.get('metric_primary')}`",
        f"- shock_scale: {pol.get('shock_scale')} · conflict_shock_scale: {pol.get('conflict_shock_scale')}",
        f"- band_active holdout: {(hold.get('band_active') or {}).get('band_hit_rate')}",
        f"- band_shock_widen holdout: {(hold.get('band_shock_widen') or {}).get('band_hit_rate')}",
        f"- band_conflict_shock_widen holdout: {(hold.get('band_conflict_shock_widen') or {}).get('band_hit_rate')}",
        f"- band_conflict_vol_widen holdout: {(hold.get('band_conflict_vol_widen') or {}).get('band_hit_rate')}",
        f"- delta conflict-widen vs active: {cmp_.get('delta_conflict_shock_widen_minus_active_band_holdout')}",
        f"- delta conflict-vol-widen vs active: {cmp_.get('delta_conflict_vol_widen_minus_active_band_holdout')}",
        f"- promotion_ready: `{doc.get('promotion_ready')}`",
        "",
        doc.get("verdict_ko") or "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--shock-scale", type=float, default=DEFAULT_SHOCK_SCALE)
    ap.add_argument("--conflict-shock-scale", type=float, default=DEFAULT_CONFLICT_SHOCK_SCALE)
    ap.add_argument("--vol-band-k", type=float, default=DEFAULT_VOL_BAND_K)
    ap.add_argument("--vol-window", type=int, default=DEFAULT_VOL_WINDOW)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not ev or not cal or not fusion:
        print("Missing eval, calendar, or fusion", file=sys.stderr)
        return 2

    rows = _scored_rows(ev)
    if len(rows) < args.n_folds:
        print(f"Insufficient scored rows ({len(rows)}) for n_folds={args.n_folds}", file=sys.stderr)
        return 2

    doc = run_conflict_band_coverage_wf(
        ev,
        cal,
        fusion,
        n_folds=args.n_folds,
        shock_scale=args.shock_scale,
        conflict_shock_scale=args.conflict_shock_scale,
        vol_band_k=args.vol_band_k,
        vol_window=args.vol_window,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "comparison": doc["comparison"],
                "promotion_ready": doc["promotion_ready"],
                "holdout_pooled": doc["holdout_pooled"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
