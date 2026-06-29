#!/usr/bin/env python3
"""RWC-enhanced Field band shadow replay — Slot 2 Phase 2 [HYPO][B-track]."""
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
from scripts.run_kospi_field_band_rwc_lite_v1 import run_rwc_lite  # noqa: E402
from scripts.run_kospi_field_band_shadow_replay_v1 import (  # noqa: E402
    ARM_ID,
    PARITY_TOL,
    _summarize_rows,
)
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import _has_conflict_surface  # noqa: E402
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import _soft_score  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_SASANG_TIER2 = ROOT / "reports/sasang_lens_veto_tier2_v1_latest.json"
DEFAULT_RWC = ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_rwc_shadow_replay_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_rwc_shadow_replay_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_field_band_rwc_shadow_replay_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_rwc_shadow_replay(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    sasang_tier2: dict[str, Any] | None = None,
    rwc_doc: dict[str, Any] | None = None,
    n_folds: int = 4,
) -> dict[str, Any]:
    if rwc_doc is None:
        rwc_doc = run_rwc_lite(
            eval_doc,
            calendar,
            fusion,
            field_tier2=field_tier2,
            n_folds=n_folds,
        )
    conflict_ids = list(((fusion.get("fusion_resolution") or {}).get("conflict_ids") or []))
    force_hold = bool((sasang_tier2 or {}).get("force_hold"))
    band_widen_only = bool((sasang_tier2 or {}).get("band_widen_only"))

    daily_rows: list[dict[str, Any]] = []
    for rwc_row in rwc_doc.get("daily_rows") or []:
        dk = str(rwc_row.get("session_date"))
        base_scale = float(rwc_row.get("band_scale_base") or 1.0)
        rwc_scale = float(rwc_row.get("band_scale_rwc") or base_scale)
        pred = str(rwc_row.get("predicted_direction"))
        actual = str(rwc_row.get("actual_direction"))
        entry: dict[str, Any] = {
            "session_date": dk,
            "arm_id": ARM_ID,
            "layer": "vol_widen_plus_rwc_lite",
            "band_scale_base": round(base_scale, 4),
            "band_scale": round(rwc_scale, 4),
            "rwc_extra_scale_factor": rwc_row.get("rwc_extra_scale_factor"),
            "widened": rwc_scale > 1.0,
            "shock_day": rwc_row.get("shock_day"),
            "conflict_surface": _has_conflict_surface(fusion),
            "conflict_ids": conflict_ids,
            "band_hit": rwc_row.get("band_hit_rwc"),
            "band_hit_vol_widen_only": rwc_row.get("band_hit_base"),
            "predicted_direction": pred,
            "actual_direction": actual,
            "direction_outcome": _outcome(pred, actual),
            "holdout_fold_day": rwc_row.get("holdout_fold_day"),
        }
        if force_hold and band_widen_only:
            entry["execution_block"] = "sasang_veto"
            entry["sasang_force_hold"] = True
        daily_rows.append(entry)

    full_summary = _summarize_rows(
        [
            {
                "band_hit": r.get("band_hit"),
                "widened": r.get("widened"),
                "direction_outcome": r.get("direction_outcome"),
            }
            for r in daily_rows
        ]
    )
    holdout_rows = [r for r in daily_rows if r.get("holdout_fold_day")]
    holdout_summary = _summarize_rows(
        [
            {
                "band_hit": r.get("band_hit"),
                "widened": r.get("widened"),
                "direction_outcome": r.get("direction_outcome"),
            }
            for r in holdout_rows
        ]
    )

    vol_only_holdout = [
        r.get("band_hit_vol_widen_only")
        for r in holdout_rows
        if isinstance(r.get("band_hit_vol_widen_only"), bool)
    ]
    vol_only_rate = (
        round(sum(1 for h in vol_only_holdout if h) / len(vol_only_holdout), 4) if vol_only_holdout else None
    )
    rwc_holdout_rate = holdout_summary.get("band_hit_rate")
    uplift = None
    if vol_only_rate is not None and rwc_holdout_rate is not None:
        uplift = round(float(rwc_holdout_rate) - float(vol_only_rate), 4)

    return {
        "schema": "kospi_field_band_rwc_shadow_replay_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "arm_id": ARM_ID,
        "layer_stack": ["band_conflict_vol_widen", "rwc_lite_post_hoc"],
        "direction_unchanged": True,
        "n_scored_total": len(daily_rows),
        "daily_rows": daily_rows,
        "summary": {
            "full_window": full_summary,
            "holdout_pooled": holdout_summary,
            "holdout_vol_widen_only_band_hit_rate": vol_only_rate,
            "holdout_rwc_uplift_pp": uplift,
            "rwc_parity": {
                "expected_holdout_band_hit_rate": (
                    ((rwc_doc.get("summary") or {}).get("holdout_pooled") or {}).get("band_hit_rate_rwc")
                ),
                "actual_holdout_band_hit_rate": rwc_holdout_rate,
                "within_tolerance": (
                    abs(float(rwc_holdout_rate) - float(expected)) <= PARITY_TOL
                    if (expected := ((rwc_doc.get("summary") or {}).get("holdout_pooled") or {}).get("band_hit_rate_rwc"))
                    is not None
                    and rwc_holdout_rate is not None
                    else None
                ),
            },
        },
        "pointers": {
            "rwc_lite": "reports/kospi_field_band_rwc_lite_v1_latest.json",
            "injection_plan": "docs/research/kospi_field_band_shadow_injection_plan_v1.md",
        },
        "reproduce": "py scripts/run_kospi_field_band_rwc_shadow_replay_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--sasang-tier2-json", type=Path, default=DEFAULT_SASANG_TIER2)
    ap.add_argument("--rwc-json", type=Path, default=DEFAULT_RWC)
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

    doc = run_rwc_shadow_replay(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        sasang_tier2=_read(args.sasang_tier2_json),
        rwc_doc=_read(args.rwc_json),
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
                "holdout_band_hit_rate": hold.get("band_hit_rate"),
                "rwc_uplift_pp": (doc.get("summary") or {}).get("holdout_rwc_uplift_pp"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
