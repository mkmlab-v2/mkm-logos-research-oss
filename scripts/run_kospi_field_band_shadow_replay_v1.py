#!/usr/bin/env python3
"""Field band_conflict_vol_widen shadow replay — day audit, no live inject [HYPO]."""
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
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import (  # noqa: E402
    DEFAULT_CONFLICT_SHOCK_SCALE,
    DEFAULT_SHOCK_SCALE,
    DEFAULT_VOL_BAND_K,
    DEFAULT_VOL_WINDOW,
    _band_hit,
    _band_hit_rate,
    _band_scale_for_mode,
    _calendar_rows,
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
from scripts.run_kospi_four_lens_shock_fusion_walkforward_v1 import blocked_folds  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_SASANG_TIER2 = ROOT / "reports/sasang_lens_veto_tier2_v1_latest.json"
DEFAULT_BAND_WF = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_shadow_replay_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_shadow_replay_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_field_band_shadow_replay_v1.jsonl"

ARM_ID = "band_conflict_vol_widen"
PARITY_TOL = 0.001


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _policy_from_tier2(field_tier2: dict[str, Any] | None) -> dict[str, Any]:
    pol = (field_tier2 or {}).get("policy") if isinstance((field_tier2 or {}).get("policy"), dict) else {}
    return {
        "arm_id": ARM_ID,
        "direction_unchanged": bool(pol.get("direction_unchanged", True)),
        "vol_band_k": float(pol.get("vol_band_k") or DEFAULT_VOL_BAND_K),
        "vol_window": int(pol.get("vol_window") or DEFAULT_VOL_WINDOW),
        "shock_scale": float(pol.get("shock_scale") or DEFAULT_SHOCK_SCALE),
        "conflict_shock_scale": float(pol.get("conflict_shock_scale") or DEFAULT_CONFLICT_SHOCK_SCALE),
        "shock_thresholds": {
            "abs_return_pct": SHOCK_RETURN_PCT,
            "prior_kospi_pct": PRIOR_SHOCK_PCT,
        },
    }


def _compute_band_scale(
    row: dict[str, Any],
    fusion: dict[str, Any],
    *,
    policy: dict[str, Any],
    ret_hist_by_date: dict[str, float],
    dates_sorted: list[str],
) -> tuple[float, bool, float | None]:
    shock = _is_shock_day(
        row,
        shock_return_pct=float(policy["shock_thresholds"]["abs_return_pct"]),
        prior_shock_pct=float(policy["shock_thresholds"]["prior_kospi_pct"]),
    )
    scale = _band_scale_for_mode(
        mode=ARM_ID,
        row=row,
        fusion=fusion,
        shock_return_pct=float(policy["shock_thresholds"]["abs_return_pct"]),
        prior_shock_pct=float(policy["shock_thresholds"]["prior_kospi_pct"]),
        shock_scale=float(policy["shock_scale"]),
        conflict_shock_scale=float(policy["conflict_shock_scale"]),
    )
    vol_pct: float | None = None
    if shock and _has_conflict_surface(fusion):
        vol_pct = _rolling_vol_pct(
            row,
            ret_hist_by_date=ret_hist_by_date,
            dates_sorted=dates_sorted,
            vol_window=int(policy["vol_window"]),
        )
        if vol_pct is not None:
            scale = max(1.0, float(policy["vol_band_k"]) * (vol_pct / 0.01))
    return scale, shock, vol_pct


def _holdout_dates(dates: list[str], n_folds: int) -> set[str]:
    out: set[str] = set()
    for _train, test in blocked_folds(dates, n_folds):
        out.update(test)
    return out


def _summarize_rows(daily_rows: list[dict[str, Any]]) -> dict[str, Any]:
    band_hits = [r.get("band_hit") for r in daily_rows]
    dir_outcomes = [str(r.get("direction_outcome") or "") for r in daily_rows]
    return {
        "n_scored": len(daily_rows),
        "widened_days": sum(1 for r in daily_rows if r.get("widened")),
        "band_hit_rate": _band_hit_rate([h if isinstance(h, bool) else None for h in band_hits]),
        "direction_soft_hit_rate": _soft_score([o for o in dir_outcomes if o]),
    }


def run_field_band_shadow_replay(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    sasang_tier2: dict[str, Any] | None = None,
    band_wf: dict[str, Any] | None = None,
    n_folds: int = 4,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    cal_by_date = _calendar_rows(calendar)
    ret_hist_by_date = {str(r["session_date"]): float(r.get("daily_return_pct") or 0.0) / 100.0 for r in rows}
    policy = _policy_from_tier2(field_tier2)
    holdout = _holdout_dates(dates, n_folds)
    conflict_ids = list(((fusion.get("fusion_resolution") or {}).get("conflict_ids") or []))
    force_hold = bool((sasang_tier2 or {}).get("force_hold"))
    band_widen_only = bool((sasang_tier2 or {}).get("band_widen_only"))

    daily_rows: list[dict[str, Any]] = []
    for row in rows:
        dk = str(row.get("session_date"))
        scale, shock_day, vol_pct = _compute_band_scale(
            row,
            fusion,
            policy=policy,
            ret_hist_by_date=ret_hist_by_date,
            dates_sorted=dates,
        )
        hit = _band_hit(row, cal_by_date.get(dk), band_scale=scale)
        pred = str(row.get("predicted_direction"))
        actual = str(row.get("actual_direction"))
        entry: dict[str, Any] = {
            "session_date": dk,
            "arm_id": ARM_ID,
            "band_scale": round(scale, 4),
            "widened": scale > 1.0,
            "shock_day": shock_day,
            "vol_pct": round(vol_pct, 6) if vol_pct is not None else None,
            "conflict_surface": _has_conflict_surface(fusion),
            "conflict_ids": conflict_ids,
            "band_hit": hit,
            "predicted_direction": pred,
            "actual_direction": actual,
            "direction_outcome": _outcome(pred, actual),
            "holdout_fold_day": dk in holdout,
        }
        if force_hold and band_widen_only:
            entry["execution_block"] = "sasang_veto"
            entry["sasang_force_hold"] = True
        daily_rows.append(entry)

    full_summary = _summarize_rows(daily_rows)
    holdout_rows = [r for r in daily_rows if r.get("holdout_fold_day")]
    holdout_summary = _summarize_rows(holdout_rows)

    wf_expected = None
    if band_wf:
        wf_arm = ((band_wf.get("holdout_pooled") or {}).get(ARM_ID) or {})
        wf_expected = wf_arm.get("band_hit_rate")
    actual_holdout = holdout_summary.get("band_hit_rate")
    parity_ok = None
    if wf_expected is not None and actual_holdout is not None:
        parity_ok = abs(float(actual_holdout) - float(wf_expected)) <= PARITY_TOL

    return {
        "schema": "kospi_field_band_shadow_replay_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "arm_id": ARM_ID,
        "policy": policy,
        "sasang_veto": {
            "force_hold": force_hold,
            "band_widen_only": band_widen_only,
            "veto_reason_codes": (sasang_tier2 or {}).get("veto_reason_codes") or [],
        },
        "config": {"n_folds": n_folds, "parity_tolerance": PARITY_TOL},
        "daily_rows": daily_rows,
        "summary": {
            "full_window": full_summary,
            "holdout_pooled": holdout_summary,
            "wf_parity": {
                "expected_band_hit_rate": wf_expected,
                "actual_band_hit_rate": actual_holdout,
                "within_tolerance": parity_ok,
            },
        },
        "pointers": {
            "eval": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
            "calendar": "reports/kospi_202606_daily_prophecy_calendar_v1.json",
            "fusion": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
            "field_tier2": "reports/field_lens_vol_band_tier2_v1_latest.json",
            "band_coverage_wf": "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json",
            "plan": "docs/research/kospi_field_band_shadow_injection_plan_v1.md",
        },
        "reproduce": "py scripts/run_kospi_field_band_shadow_replay_v1.py",
        "ladder_stage": "L1_shadow_replay",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--sasang-tier2-json", type=Path, default=DEFAULT_SASANG_TIER2)
    ap.add_argument("--band-wf-json", type=Path, default=DEFAULT_BAND_WF)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--skip-parity-check", action="store_true")
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

    doc = run_field_band_shadow_replay(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        sasang_tier2=_read(args.sasang_tier2_json),
        band_wf=_read(args.band_wf_json),
        n_folds=args.n_folds,
    )

    parity = (doc.get("summary") or {}).get("wf_parity") or {}
    if not args.skip_parity_check and parity.get("within_tolerance") is False:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "wf_parity_failed",
                    "wf_parity": parity,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for row in doc.get("daily_rows") or []:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "holdout_band_hit_rate": (doc.get("summary") or {}).get("holdout_pooled", {}).get("band_hit_rate"),
                "wf_parity": parity,
                "widened_days": (doc.get("summary") or {}).get("full_window", {}).get("widened_days"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
