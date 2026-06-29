#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stress-conditional shadow replay: active vs field+momentum shadow on stress days [HYPO].

Compares applied active arm vs research_shadow (default v2_field_momentum_4ai_legacy_hold)
on scored June forward days, split by stress vs calm subsets.

Stress tags (union):
- abs_return_stress: |daily_return_pct| >= threshold
- prior_vol_stress: 5d log-return stdev before session > vol threshold
- active_fail: applied arm outcome FAIL

research_only · auto_apply forbidden · send_gate HOLD.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PANEL = ROOT / "reports/kospi_june2026_shadow_candidate_panel_latest.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_stress_conditional_shadow_replay_v1_latest.json"
DEFAULT_SHADOW = "v2_field_momentum_4ai_legacy_hold"
SCHEMA = "kospi_june2026_stress_conditional_shadow_replay_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _soft_score(outcome: str) -> float:
    if outcome == "HIT":
        return 1.0
    if outcome == "NEUTRAL_DRAW":
        return 0.5
    return 0.0


def _hit_rate(outcomes: list[str]) -> float | None:
    directional = [o for o in outcomes if o in ("HIT", "FAIL")]
    if not directional:
        return None
    return round(sum(1 for o in directional if o == "HIT") / len(directional), 4)


def _soft_hit_rate(outcomes: list[str]) -> float | None:
    if not outcomes:
        return None
    return round(sum(_soft_score(o) for o in outcomes) / len(outcomes), 4)


def _load_kospi_series(path: Path) -> tuple[list[str], list[float]]:
    if not path.is_file():
        return [], []
    dates: list[str] = []
    closes: list[float] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date") or row.get("date") or "")[:10]
            raw = row.get("Close") or row.get("close")
            if len(dk) != 10 or raw in (None, ""):
                continue
            try:
                dates.append(dk)
                closes.append(float(raw))
            except (ValueError, TypeError):
                continue
    return dates, closes


def _prior_vol_stress(
    dates: list[str],
    closes: list[float],
    session_date: str,
    *,
    window: int,
    threshold: float,
) -> tuple[bool, float | None]:
    try:
        idx = dates.index(session_date)
    except ValueError:
        return False, None
    if idx < window + 1:
        return False, None
    rets: list[float] = []
    for i in range(idx - window, idx):
        prev, cur = closes[i - 1], closes[i]
        if prev <= 0 or cur <= 0:
            continue
        rets.append(math.log(cur / prev))
    if len(rets) < 2:
        return False, None
    rv = statistics.stdev(rets)
    return rv > threshold, round(rv, 6)


def _arm_outcomes(day: dict[str, Any], arm_id: str) -> str | None:
    for arm in day.get("arms") or []:
        if isinstance(arm, dict) and str(arm.get("arm_id")) == arm_id:
            return str(arm.get("outcome") or "")
    return None


def _subset_metrics(outcomes: list[str]) -> dict[str, Any]:
    return {
        "n": len(outcomes),
        "directional_hit_rate": _hit_rate(outcomes),
        "soft_hit_rate": _soft_hit_rate(outcomes),
        "hit": sum(1 for o in outcomes if o == "HIT"),
        "fail": sum(1 for o in outcomes if o == "FAIL"),
        "neutral_draw": sum(1 for o in outcomes if o == "NEUTRAL_DRAW"),
    }


def _monthly_vol_p75(
    days_in: list[dict[str, Any]],
    dates: list[str],
    closes: list[float],
    *,
    window: int,
) -> float | None:
    vols: list[float] = []
    for day in days_in:
        if not isinstance(day, dict):
            continue
        dk = str(day.get("session_date") or "")
        _, rv = _prior_vol_stress(dates, closes, dk, window=window, threshold=0.0)
        if rv is not None:
            vols.append(rv)
    if len(vols) < 4:
        return None
    vols.sort()
    idx = int(0.75 * (len(vols) - 1))
    return vols[idx]


def build_stress_replay(
    *,
    panel_doc: dict[str, Any],
    eval_doc: dict[str, Any],
    kospi_csv: Path,
    shadow_candidate_id: str,
    abs_return_threshold_pct: float,
    vol_window: int,
    vol_threshold: float,
) -> dict[str, Any]:
    applied_id = str(panel_doc.get("applied_active_id") or "v2_lens3_heavy")
    arm_diff = panel_doc.get("scored_day_arm_diff") if isinstance(panel_doc.get("scored_day_arm_diff"), dict) else {}
    days_in = arm_diff.get("days") if isinstance(arm_diff.get("days"), list) else []

    eval_by_date: dict[str, dict[str, Any]] = {}
    for row in eval_doc.get("rows") or []:
        if isinstance(row, dict) and row.get("session_date"):
            eval_by_date[str(row["session_date"])] = row

    dates, closes = _load_kospi_series(kospi_csv)
    adaptive_vol_thr = _monthly_vol_p75(days_in, dates, closes, window=vol_window)
    effective_vol_thr = max(vol_threshold, adaptive_vol_thr or 0.0)

    replay_days: list[dict[str, Any]] = []
    for day in days_in:
        if not isinstance(day, dict):
            continue
        dk = str(day.get("session_date") or "")
        if not dk:
            continue
        eval_row = eval_by_date.get(dk, {})
        ret_pct = eval_row.get("daily_return_pct")
        try:
            ret_f = float(ret_pct) if ret_pct is not None else None
        except (ValueError, TypeError):
            ret_f = None

        reasons: list[str] = []
        market_reasons: list[str] = []
        if ret_f is not None and abs(ret_f) >= abs_return_threshold_pct:
            reasons.append("abs_return_stress")
            market_reasons.append("abs_return_stress")

        vol_hit, rv = _prior_vol_stress(
            dates, closes, dk, window=vol_window, threshold=effective_vol_thr
        )
        if vol_hit:
            reasons.append("prior_vol_stress")
            market_reasons.append("prior_vol_stress")

        active_out = _arm_outcomes(day, applied_id) or ""
        if active_out == "FAIL":
            reasons.append("active_fail")

        shadow_out = _arm_outcomes(day, shadow_candidate_id) or ""
        is_market_stress = bool(market_reasons)
        is_stress = bool(reasons)
        active_soft = _soft_score(active_out)
        shadow_soft = _soft_score(shadow_out)

        replay_days.append(
            {
                "session_date": dk,
                "actual_direction": day.get("actual_direction"),
                "daily_return_pct": ret_f,
                "prior_vol_5d_stdev": rv,
                "stress": is_stress,
                "market_stress": is_market_stress,
                "stress_reasons": reasons,
                "market_stress_reasons": market_reasons,
                "active_arm_id": applied_id,
                "active_outcome": active_out,
                "shadow_arm_id": shadow_candidate_id,
                "shadow_outcome": shadow_out,
                "shadow_soft_delta_vs_active": round(shadow_soft - active_soft, 4),
                "shadow_would_beat_active": shadow_soft > active_soft,
                "shadow_direction_diff": any(
                    isinstance(a, dict)
                    and str(a.get("arm_id")) == shadow_candidate_id
                    and a.get("direction_diff_vs_active")
                    for a in (day.get("arms") or [])
                ),
            }
        )

    stress_days = [d for d in replay_days if d.get("market_stress")]
    calm_days = [d for d in replay_days if not d.get("market_stress")]
    active_fail_days = [d for d in replay_days if d.get("active_outcome") == "FAIL"]

    def collect(subset: list[dict[str, Any]], key: str) -> list[str]:
        return [str(d.get(key) or "") for d in subset if d.get(key)]

    stress_active = _subset_metrics(collect(stress_days, "active_outcome"))
    stress_shadow = _subset_metrics(collect(stress_days, "shadow_outcome"))
    calm_active = _subset_metrics(collect(calm_days, "active_outcome"))
    calm_shadow = _subset_metrics(collect(calm_days, "shadow_outcome"))
    all_active = _subset_metrics(collect(replay_days, "active_outcome"))
    all_shadow = _subset_metrics(collect(replay_days, "shadow_outcome"))

    def _delta(shadow_m: dict[str, Any], active_m: dict[str, Any]) -> float | None:
        s, a = shadow_m.get("soft_hit_rate"), active_m.get("soft_hit_rate")
        if s is None or a is None:
            return None
        return round(float(s) - float(a), 4)

    n_shadow_rescue = sum(
        1 for d in active_fail_days if d.get("shadow_would_beat_active")
    )
    n_active_fail = len(active_fail_days)

    note_ko = (
        f"market_stress일({len(stress_days)}일) shadow soft HR {stress_shadow.get('soft_hit_rate')} vs "
        f"active {stress_active.get('soft_hit_rate')}; calm일({len(calm_days)}일) shadow "
        f"{calm_shadow.get('soft_hit_rate')} vs active {calm_active.get('soft_hit_rate')}. "
        f"active_fail {n_active_fail}일 중 shadow rescue {n_shadow_rescue}일. 연구 전용·auto apply 금지."
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": panel_doc.get("year_month") or eval_doc.get("year_month"),
        "applied_active_id": applied_id,
        "shadow_candidate_id": shadow_candidate_id,
        "stress_policy": {
            "abs_return_threshold_pct": abs_return_threshold_pct,
            "vol_window_trading_days": vol_window,
            "vol_stdev_threshold_floor": vol_threshold,
            "vol_stdev_threshold_effective": round(effective_vol_thr, 6),
            "vol_stdev_threshold_adaptive_p75": round(adaptive_vol_thr, 6) if adaptive_vol_thr else None,
            "market_stress_union": ["abs_return_stress", "prior_vol_stress"],
            "active_fail_tracked_separately": True,
        },
        "n_scored_days": len(replay_days),
        "all_scored": {
            "active": all_active,
            "shadow": all_shadow,
            "soft_delta_shadow_minus_active": _delta(all_shadow, all_active),
        },
        "stress_subset": {
            "n_days": len(stress_days),
            "label": "market_stress",
            "active": stress_active,
            "shadow": stress_shadow,
            "soft_delta_shadow_minus_active": _delta(stress_shadow, stress_active),
        },
        "active_fail_subset": {
            "n_days": n_active_fail,
            "active": _subset_metrics(collect(active_fail_days, "active_outcome")),
            "shadow": _subset_metrics(collect(active_fail_days, "shadow_outcome")),
            "soft_delta_shadow_minus_active": _delta(
                _subset_metrics(collect(active_fail_days, "shadow_outcome")),
                _subset_metrics(collect(active_fail_days, "active_outcome")),
            ),
            "n_shadow_rescue_on_active_fail": n_shadow_rescue,
        },
        "calm_subset": {
            "n_days": len(calm_days),
            "active": calm_active,
            "shadow": calm_shadow,
            "soft_delta_shadow_minus_active": _delta(calm_shadow, calm_active),
        },
        "days": replay_days,
        "recommendation": {
            "ready_for_apply_review": False,
            "blockers": [
                "research_shadow_only",
                "stress_subset_sample_may_be_small",
                "no_track_a_auto_merge",
            ],
            "note_ko": note_ko,
        },
        "sources": {
            "shadow_panel": str(DEFAULT_PANEL.relative_to(ROOT)).replace("\\", "/"),
            "eval": str(DEFAULT_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "kospi_csv": str(kospi_csv.relative_to(ROOT)).replace("\\", "/") if kospi_csv.is_file() else str(kospi_csv),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--shadow-candidate-id", default=DEFAULT_SHADOW)
    ap.add_argument("--abs-return-threshold-pct", type=float, default=1.5)
    ap.add_argument("--vol-window", type=int, default=5)
    ap.add_argument("--vol-threshold", type=float, default=0.015)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    panel = _read_json(args.panel_json if args.panel_json.is_absolute() else ROOT / args.panel_json)
    if panel.get("schema") != "kospi_june2026_shadow_candidate_panel_v1":
        print(f"missing or invalid panel: {args.panel_json}", file=sys.stderr)
        return 2

    eval_doc = _read_json(args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json)
    if eval_doc.get("schema") != "kospi_june2026_daily_prophecy_eval_v1":
        print(f"missing or invalid eval: {args.eval_json}", file=sys.stderr)
        return 2

    kospi = args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv
    doc = build_stress_replay(
        panel_doc=panel,
        eval_doc=eval_doc,
        kospi_csv=kospi,
        shadow_candidate_id=str(args.shadow_candidate_id),
        abs_return_threshold_pct=float(args.abs_return_threshold_pct),
        vol_window=max(2, int(args.vol_window)),
        vol_threshold=float(args.vol_threshold),
    )
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "n_scored": doc["n_scored_days"],
                "n_stress": doc["stress_subset"]["n_days"],
                "stress_soft_delta": doc["stress_subset"].get("soft_delta_shadow_minus_active"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
