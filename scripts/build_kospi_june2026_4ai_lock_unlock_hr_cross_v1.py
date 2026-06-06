#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June 2026 KOSPI 4AI lock vs unlock vs v2-only HR cross-table [HYPO][research_only]."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_neutral_research_bundle_v1 import (  # noqa: E402
    _resolve_calendar_path,
    four_ai_counterfactual,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import (  # noqa: E402
    _default_as_of_kst,
    eval_calendar,
)
import scripts.kospi_june_4ai_prophecy_overlay_v1 as overlay  # noqa: E402

EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
JUNE_BACKTEST = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"
READINESS = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_4ai_lock_unlock_hr_cross_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metrics_from_backtest(doc: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    for row in doc.get("variants") or []:
        if row.get("variant_id") == variant_id:
            return row.get("metrics")
    return None


def _eval_overlay_directions(
    calendar: dict[str, Any],
    overlay_doc: dict[str, Any],
    *,
    as_of_kst: str,
) -> dict[str, Any]:
    by_date = {str(r.get("session_date")): r for r in overlay_doc.get("rows") or []}
    cal_copy = copy.deepcopy(calendar)
    for row in cal_copy.get("rows") or []:
        dk = str(row.get("session_date") or "")
        orow = by_date.get(dk) or {}
        if orow.get("four_ai_direction") is not None:
            row["predicted_direction"] = str(orow["four_ai_direction"])
    ev = eval_calendar(cal_copy, as_of_kst=as_of_kst)
    return {
        "n_scored": ev.get("n_scored"),
        "metrics": ev.get("metrics"),
    }


def build_cross(
    *,
    calendar_path: Path,
    as_of_kst: str,
    year_month: str = "2026-06",
) -> dict[str, Any]:
    rules = _read_json(EVOLUTION_RULES)
    calendar = _read_json(calendar_path)
    if not calendar.get("rows"):
        raise SystemExit(f"calendar empty or missing: {calendar_path}")

    eval_doc = eval_calendar(calendar, calendar_path=calendar_path, as_of_kst=as_of_kst)
    cf = four_ai_counterfactual(calendar, evolution_path=EVOLUTION_RULES, eval_doc=eval_doc)

    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    coord_base = (
        rules.get("four_ai_coordinator_policy")
        if isinstance(rules.get("four_ai_coordinator_policy"), dict)
        else {}
    )
    locked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": True}
    unlocked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": False}

    locked_overlay = overlay.build_4ai_report(
        calendar,
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=locked_pol,
    )
    unlocked_overlay = overlay.build_4ai_report(
        calendar,
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=unlocked_pol,
    )

    forward_locked = _eval_overlay_directions(calendar, locked_overlay, as_of_kst=as_of_kst)
    forward_unlocked = _eval_overlay_directions(calendar, unlocked_overlay, as_of_kst=as_of_kst)

    june_bt = _read_json(JUNE_BACKTEST)
    backtest_rows = {
        "v2_lens3_heavy_no_4ai": _metrics_from_backtest(june_bt, "v2_lens3_heavy"),
        "v2_lens3_heavy_4ai_current": _metrics_from_backtest(june_bt, "v2_lens3_heavy_4ai_current"),
        "v2_lens3_heavy_4ai_legacy": _metrics_from_backtest(june_bt, "v2_lens3_heavy_4ai_legacy_hold"),
    }

    readiness = _read_json(READINESS)
    fs = readiness.get("forward_scoring") if isinstance(readiness.get("forward_scoring"), dict) else {}
    n_scored = int(eval_doc.get("n_scored") or 0)
    min_required = int(fs.get("min_required") or 15)
    partial = n_scored < min_required

    v2_soft = (eval_doc.get("metrics") or {}).get("soft_hit_rate")
    locked_soft = (forward_locked.get("metrics") or {}).get("soft_hit_rate")
    unlocked_soft = (forward_unlocked.get("metrics") or {}).get("soft_hit_rate")

    return {
        "schema": "kospi_june2026_4ai_lock_unlock_hr_cross_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "gpu_used": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "calendar_path": str(calendar_path.relative_to(ROOT)).replace("\\", "/"),
        "forward_gate": {
            "n_scored": n_scored,
            "min_required": min_required,
            "partial": partial,
            "projected_gate_session_date": fs.get("projected_gate_session_date"),
            "note_ko": (
                f"partial forward n={n_scored}/{min_required} — full A1/A4 cross는 gate 통과 후 재실행"
                if partial
                else "forward gate 충족 — cross 신뢰도 상향"
            ),
        },
        "published_v2_eval": {
            "n_scored": eval_doc.get("n_scored"),
            "metrics": eval_doc.get("metrics"),
        },
        "forward_four_ai_eval": {
            "locked_to_v2": forward_locked,
            "unlocked": forward_unlocked,
            "soft_delta_unlock_minus_v2": round(float(unlocked_soft or 0) - float(v2_soft or 0), 4)
            if unlocked_soft is not None and v2_soft is not None
            else None,
            "soft_delta_unlock_minus_locked": round(float(unlocked_soft or 0) - float(locked_soft or 0), 4)
            if unlocked_soft is not None and locked_soft is not None
            else None,
        },
        "four_ai_counterfactual": cf,
        "nov_may_backtest_soft_hr": backtest_rows,
        "comparison_ko": {
            "v2_only_soft_forward": v2_soft,
            "four_ai_locked_soft_forward": locked_soft,
            "four_ai_unlocked_soft_forward": unlocked_soft,
            "unlock_would_change_v2_days": cf.get("n_unlocked_would_change_v2"),
            "n_lock_vs_unlock_diffs": cf.get("n_direction_diffs_lock_vs_unlock"),
        },
        "verdict_ko": (
            "June forward partial — 4AI unlock live apply 금지; lock=current published v2 정렬."
            if partial
            else "June forward gate 충족 — unlock shadow Δ 재검토 가능하나 human sign-off 없이 apply 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--as-of-kst", default=None, help="Default: last KRX session on or before today (KST)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month).resolve()
    as_of = args.as_of_kst or _default_as_of_kst()

    doc = build_cross(calendar_path=cal_path, as_of_kst=as_of, year_month=args.year_month)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cmp_ko = doc.get("comparison_ko") or {}
    fg = doc.get("forward_gate") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"n_scored={fg.get('n_scored')}/{fg.get('min_required')} "
        f"partial={fg.get('partial')} "
        f"unlock_change_v2_days={cmp_ko.get('unlock_would_change_v2_days')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
