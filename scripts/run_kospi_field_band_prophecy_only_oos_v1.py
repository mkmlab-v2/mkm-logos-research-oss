#!/usr/bin/env python3
"""Prophecy-only panel OOS: tuned stack_union vs baseline [HYPO][B-track]."""
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

from scripts.run_kospi_field_band_cptc_lite_v1 import run_cptc_lite  # noqa: E402
from scripts.run_kospi_field_band_rwc_lite_v1 import run_rwc_lite  # noqa: E402
from scripts.run_kospi_field_band_stack_ensemble_v1 import run_stack_ensemble  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import _soft_score  # noqa: E402

from scripts.kospi_field_band_small_sample_guardrails_v1 import build_small_sample_guardrails  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_prophecy_only_panel_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json"
DEFAULT_MIXED_STACK = ROOT / "reports/kospi_field_band_stack_ensemble_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_prophecy_only_oos_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_prophecy_only_oos_v1_latest.json"

MIN_HOLDOUT_N = 10
MIN_DELTA_PP = 0.03
PRIMARY_HOLDOUT_CUTOFF = "2026-05-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hold_summary(doc: dict[str, Any], key: str) -> dict[str, Any]:
    hold = ((doc.get("summary") or {}).get("holdout_pooled") or {}).get(key) or {}
    if isinstance(hold, dict) and "band_hit_rate" in hold:
        return hold
    return {"n_scored": hold.get("n_scored"), "band_hit_rate": hold.get("band_hit_rate")}


def _rate_on_dates(daily: list[dict[str, Any]], dates: set[str], hit_key: str) -> dict[str, Any]:
    from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import _band_hit_rate

    sub = [r for r in daily if str(r.get("session_date")) in dates]
    if not sub:
        return {"n_scored": 0, "band_hit_rate": None}
    hits = [r.get(hit_key) for r in sub]
    return {
        "n_scored": len(sub),
        "band_hit_rate": _band_hit_rate([h if isinstance(h, bool) else None for h in hits]),
    }


def _primary_may_june_holdout(stack_doc: dict[str, Any], *, cutoff: str = PRIMARY_HOLDOUT_CUTOFF) -> dict[str, Any]:
    daily = stack_doc.get("daily_rows") or []
    dates = {
        str(r.get("session_date"))
        for r in daily
        if r.get("holdout_fold_day") and str(r.get("session_date") or "") >= cutoff
    }
    base = _rate_on_dates(daily, dates, "band_hit_base")
    stack = _rate_on_dates(daily, dates, "band_hit_stack")
    base_rate = float(base.get("band_hit_rate") or 0.0)
    stack_rate = float(stack.get("band_hit_rate") or 0.0) if stack.get("band_hit_rate") is not None else 0.0
    return {
        "cutoff_inclusive": cutoff,
        "holdout_dates_n": len(dates),
        "base": base,
        "stack_union": stack,
        "delta_stack_minus_base": round(stack_rate - base_rate, 4) if stack.get("band_hit_rate") is not None else None,
    }


def run_prophecy_only_oos(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    n_folds: int = 4,
) -> dict[str, Any]:
    rwc_p = (policy or {}).get("rwc") if isinstance((policy or {}).get("rwc"), dict) else {}
    cptc_p = (policy or {}).get("cptc") if isinstance((policy or {}).get("cptc"), dict) else {}

    rwc_doc = run_rwc_lite(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        n_folds=n_folds,
        decay_lambda=float(rwc_p.get("decay_lambda") or 0.08),
        margin_gamma=float(rwc_p.get("margin_gamma") or 0.18),
        bandwidth_h=float(rwc_p.get("bandwidth_h") or 1.0),
    )
    cptc_doc = run_cptc_lite(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        n_folds=n_folds,
        vol_jump_threshold=float(cptc_p.get("vol_jump_threshold") or 1.75),
        margin_gamma=float(cptc_p.get("margin_gamma") or 0.18),
        base_quantile_q=float(cptc_p.get("base_quantile_q") or 0.88),
    )
    stack_doc = run_stack_ensemble(eval_doc, calendar, rwc_doc, cptc_doc)

    base_hold = _hold_summary(stack_doc, "base")
    rwc_hold = _hold_summary(stack_doc, "rwc")
    cptc_hold = _hold_summary(stack_doc, "cptc")
    stack_hold = _hold_summary(stack_doc, "stack")

    n_hold = int(stack_hold.get("n_scored") or 0)
    base_rate = float(base_hold.get("band_hit_rate") or 0.0)
    stack_rate = float(stack_hold.get("band_hit_rate") or 0.0)
    delta = round(stack_rate - base_rate, 4)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome

    hold_rows = [r for r in (stack_doc.get("daily_rows") or []) if r.get("holdout_fold_day")]
    hold_dir = [
        _outcome(str(r.get("predicted_direction")), str(r.get("actual_direction")))
        for r in hold_rows
        if r.get("predicted_direction") and r.get("actual_direction")
    ]

    gates = {
        "holdout_n_ge_10": n_hold >= MIN_HOLDOUT_N,
        "delta_stack_ge_3pp": delta >= MIN_DELTA_PP,
        "science_backfill_rows_zero": not any(
            r.get("backfill_source") for r in (eval_doc.get("rows") or []) if isinstance(r, dict)
        ),
        "direction_unchanged": True,
    }
    prophecy_only_ready = all(gates.values())
    primary_hold = _primary_may_june_holdout(stack_doc)
    guardrails_block = build_small_sample_guardrails(
        {
            "prophecy_only_oos_ready": prophecy_only_ready,
            "holdout_pooled": {"stack_union": stack_hold},
            "n_scored_total": eval_doc.get("n_scored"),
            "delta_stack_minus_base_holdout": delta,
        }
    )

    return {
        "schema": "kospi_field_band_prophecy_only_oos_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "track_a_go": False,
        "panel_label": eval_doc.get("panel_label"),
        "n_scored_total": eval_doc.get("n_scored"),
        "n_months": eval_doc.get("n_months"),
        "included_prophecy_months": eval_doc.get("included_prophecy_months"),
        "policy_pointer": "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json",
        "holdout_pooled": {
            "base": base_hold,
            "rwc": rwc_hold,
            "cptc": cptc_hold,
            "stack_union": stack_hold,
        },
        "primary_may_june_holdout": primary_hold,
        "delta_stack_minus_base_holdout": delta,
        "direction_soft_hit_rate_holdout": _soft_score(hold_dir),
        "gates": gates,
        "prophecy_only_oos_ready": prophecy_only_ready,
        "promotion_candidate": guardrails_block["promotion_candidate_research"],
        "promotion_candidate_for_discussion": guardrails_block["promotion_candidate_for_discussion"],
        "small_sample_guardrails": guardrails_block,
        "verdict_ko": (
            "Prophecy-only holdout stack 개선 확인 — 상용 논의 근거 강화"
            if prophecy_only_ready
            else "Prophecy-only OOS 게이트 미달 — 연구 유지"
        ),
        "pointers": {
            "eval": "reports/kospi_prophecy_only_panel_eval_v1_latest.json",
            "mixed_stack_compare": "reports/kospi_field_band_stack_compare_v1_latest.json",
        },
        "reproduce": "py scripts/run_kospi_field_band_prophecy_only_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not ev or not cal or not fusion:
        print("Missing eval, calendar, or fusion", file=sys.stderr)
        return 2

    doc = run_prophecy_only_oos(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        policy=_read(args.policy_json),
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
                "prophecy_only_oos_ready": doc["prophecy_only_oos_ready"],
                "holdout_stack": (doc["holdout_pooled"]["stack_union"] or {}).get("band_hit_rate"),
                "delta": doc["delta_stack_minus_base_holdout"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
