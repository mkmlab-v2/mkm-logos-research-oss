#!/usr/bin/env python3
"""Stack ensemble: union widen of RWC-lite + CPTC-lite on Field band [HYPO][B-track]."""
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

from scripts.run_kospi_field_band_shadow_replay_v1 import ARM_ID, _holdout_dates  # noqa: E402
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
DEFAULT_RWC = ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json"
DEFAULT_CPTC = ROOT / "reports/kospi_field_band_cptc_lite_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_stack_ensemble_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_field_band_stack_ensemble_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_stack_ensemble(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    rwc_doc: dict[str, Any],
    cptc_doc: dict[str, Any],
    *,
    n_folds: int = 4,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    cal_by_date = _calendar_rows(calendar)
    holdout = _holdout_dates(dates, n_folds)
    rwc_by = {str(r["session_date"]): r for r in (rwc_doc.get("daily_rows") or [])}
    cptc_by = {str(r["session_date"]): r for r in (cptc_doc.get("daily_rows") or [])}

    daily: list[dict[str, Any]] = []
    for row in rows:
        dk = str(row.get("session_date"))
        rwc_row = rwc_by.get(dk) or {}
        cptc_row = cptc_by.get(dk) or {}
        base = float(rwc_row.get("band_scale_base") or cptc_row.get("band_scale_base") or 1.0)
        rwc_scale = float(rwc_row.get("band_scale_rwc") or base)
        cptc_scale = float(cptc_row.get("band_scale_cptc") or base)
        stack_scale = max(rwc_scale, cptc_scale)
        stack_source = "rwc" if rwc_scale >= cptc_scale else "cptc"
        if abs(rwc_scale - cptc_scale) < 1e-6:
            stack_source = "tie"

        cal_row = cal_by_date.get(dk)
        base_hit = rwc_row.get("band_hit_base")
        if base_hit is None:
            base_hit = _band_hit(row, cal_row, band_scale=base)
        stack_hit = _band_hit(row, cal_row, band_scale=stack_scale)

        daily.append(
            {
                "session_date": dk,
                "arm_id": ARM_ID,
                "band_scale_base": round(base, 4),
                "band_scale_rwc": round(rwc_scale, 4),
                "band_scale_cptc": round(cptc_scale, 4),
                "band_scale_stack": round(stack_scale, 4),
                "stack_widen_source": stack_source,
                "band_hit_base": base_hit,
                "band_hit_rwc": rwc_row.get("band_hit_rwc"),
                "band_hit_cptc": cptc_row.get("band_hit_cptc"),
                "band_hit_stack": stack_hit,
                "holdout_fold_day": dk in holdout,
                "predicted_direction": row.get("predicted_direction"),
                "actual_direction": row.get("actual_direction"),
            }
        )

    def _summarize(sub: list[dict[str, Any]], hit_key: str) -> dict[str, Any]:
        if not sub:
            return {"n_scored": 0, "band_hit_rate": None}
        hits = [r.get(hit_key) for r in sub]
        return {
            "n_scored": len(sub),
            "band_hit_rate": _band_hit_rate([h if isinstance(h, bool) else None for h in hits]),
        }

    hold_rows = [r for r in daily if r.get("holdout_fold_day")]
    hold_base = _summarize(hold_rows, "band_hit_base")
    hold_rwc = _summarize(hold_rows, "band_hit_rwc")
    hold_cptc = _summarize(hold_rows, "band_hit_cptc")
    hold_stack = _summarize(hold_rows, "band_hit_stack")

    base_rate = float(hold_base.get("band_hit_rate") or 0.0)
    stack_rate = float(hold_stack.get("band_hit_rate") or 0.0)
    delta = round(stack_rate - base_rate, 4)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome

    hold_dir = [
        _outcome(p, a)
        for p, a in zip(
            [r.get("predicted_direction") for r in hold_rows],
            [r.get("actual_direction") for r in hold_rows],
        )
    ]

    promotion_candidate = delta >= 0.03 and int(hold_stack.get("n_scored") or 0) >= 30

    return {
        "schema": "kospi_field_band_stack_ensemble_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "arm_id": ARM_ID,
        "layer": "field_band_rwc_cptc_union_widen",
        "direction_unchanged": True,
        "combine_rule": "band_scale_stack = max(band_scale_rwc, band_scale_cptc)",
        "n_scored_total": len(daily),
        "daily_rows": daily,
        "summary": {
            "full_window": {
                "base": _summarize(daily, "band_hit_base"),
                "rwc": _summarize(daily, "band_hit_rwc"),
                "cptc": _summarize(daily, "band_hit_cptc"),
                "stack": _summarize(daily, "band_hit_stack"),
            },
            "holdout_pooled": {
                "base": hold_base,
                "rwc": hold_rwc,
                "cptc": hold_cptc,
                "stack": hold_stack,
            },
            "delta_stack_minus_base_holdout": delta,
            "delta_stack_minus_rwc_holdout": round(
                stack_rate - float(hold_rwc.get("band_hit_rate") or 0.0), 4
            ),
            "direction_soft_hit_rate_holdout": _soft_score(hold_dir),
        },
        "promotion_candidate": promotion_candidate,
        "verdict_ko": (
            "Stack union widen holdout band 개선 — RWC/CPTC 중 강한 쪽 채택"
            if promotion_candidate
            else "Stack ensemble holdout 개선 미달"
        ),
        "pointers": {
            "rwc_lite": "reports/kospi_field_band_rwc_lite_v1_latest.json",
            "cptc_lite": "reports/kospi_field_band_cptc_lite_v1_latest.json",
            "stack_compare": "reports/kospi_field_band_stack_compare_v1_latest.json",
        },
        "reproduce": "py scripts/run_kospi_field_band_stack_ensemble_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--rwc-json", type=Path, default=DEFAULT_RWC)
    ap.add_argument("--cptc-json", type=Path, default=DEFAULT_CPTC)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    rwc = _read(args.rwc_json)
    cptc = _read(args.cptc_json)
    if not all((ev, cal, rwc, cptc)):
        print("Missing eval, calendar, rwc, or cptc", file=sys.stderr)
        return 2

    doc = run_stack_ensemble(ev, cal, rwc, cptc, n_folds=args.n_folds)
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
                "holdout_stack": (hold.get("stack") or {}).get("band_hit_rate"),
                "delta": (doc.get("summary") or {}).get("delta_stack_minus_base_holdout"),
                "promotion_candidate": doc.get("promotion_candidate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
