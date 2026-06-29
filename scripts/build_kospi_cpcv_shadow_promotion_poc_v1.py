#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CPCV-style shadow promotion PoC — composite vs active across OOS path splits [HYPO].

Uses merged 2026-01..06 calendars. No training; evaluates stability of composite_bear_conditional
soft HR delta across combinatorial test-group holds (López de Prado CPCV simplified).

research_only · send_gate HOLD · NOT Track A apply.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import build_bundle  # noqa: E402
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import _resolve_calendar_path  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_HERO = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_cpcv_shadow_promotion_poc_v1_latest.json"
MERGE_MONTHS_DEFAULT = ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _calendar_path_for_month(year_month: str) -> Path | None:
    tag = year_month.replace("-", "")
    for name in (
        f"kospi_{tag}_daily_prophecy_calendar_v1.json",
        f"kospi_{tag}_daily_prophecy_calendar_research.json",
    ):
        p = ROOT / "reports" / name
        if p.is_file():
            return p
    return None


def merge_calendars(year_months: tuple[str, ...]) -> dict[str, Any]:
    rows_by: dict[str, dict[str, Any]] = {}
    trading: list[str] = []
    profiles: list[str] = []
    for ym in year_months:
        p = _calendar_path_for_month(ym)
        if not p:
            continue
        cal = _read(p)
        profiles.append(str(cal.get("multilens_profile") or "v2_multilens"))
        for dk in cal.get("trading_days") or []:
            if dk not in trading:
                trading.append(str(dk))
        for row in cal.get("rows") or []:
            if not isinstance(row, dict):
                continue
            dk = str(row.get("session_date") or "")[:10]
            if len(dk) == 10:
                rows_by[dk] = row
    trading.sort()
    rows = [rows_by[d] for d in trading if d in rows_by]
    return {
        "schema": "kospi_merged_prophecy_calendar_v1",
        "year_month": "merged",
        "merged_from": list(year_months),
        "multilens_profile": profiles[0] if profiles else "v2_multilens",
        "trading_days": trading,
        "rows": rows,
    }


def _metrics_from_outcomes(outcomes: list[str]) -> dict[str, Any]:
    if not outcomes:
        return {"n": 0, "soft_hit_rate": None}
    soft = sum(1.0 if o == "HIT" else 0.5 if o == "NEUTRAL_DRAW" else 0.0 for o in outcomes) / len(outcomes)
    n_dir = sum(1 for o in outcomes if o in ("HIT", "FAIL"))
    hits = sum(1 for o in outcomes if o == "HIT")
    return {
        "n": len(outcomes),
        "soft_hit_rate": round(soft, 4),
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "hit": hits,
        "fail": sum(1 for o in outcomes if o == "FAIL"),
        "neutral_draw": sum(1 for o in outcomes if o == "NEUTRAL_DRAW"),
    }


def _split_groups(dates: list[str], n_groups: int) -> list[list[str]]:
    if not dates or n_groups < 1:
        return []
    n = len(dates)
    base, rem = divmod(n, n_groups)
    groups: list[list[str]] = []
    idx = 0
    for g in range(n_groups):
        size = base + (1 if g < rem else 0)
        groups.append(dates[idx : idx + size])
        idx += size
    return groups


def build_cpcv_poc(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    flow: dict[str, float | None],
    hero_cal: dict[str, Any],
    as_of_kst: str,
    n_groups: int = 6,
    n_test_groups: int = 2,
    arm_id: str = "composite_bear_conditional",
    min_fold_n: int = 5,
) -> dict[str, Any]:
    bundle = build_bundle(
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        flow=flow,
        hero_cal=hero_cal,
        as_of_kst=as_of_kst,
        year_month="merged_cpcv",
    )
    day_by = {str(d["session_date"]): d for d in bundle.get("days") or []}
    scored_dates = sorted(day_by.keys())
    groups = _split_groups(scored_dates, n_groups)
    if len(groups) < n_test_groups + 1:
        return {
            "schema": "kospi_cpcv_shadow_promotion_poc_v1",
            "error": "insufficient_groups",
            "n_scored": len(scored_dates),
        }

    folds: list[dict[str, Any]] = []
    deltas: list[float] = []
    for test_idx in combinations(range(len(groups)), n_test_groups):
        test_dates = sorted(d for gi in test_idx for d in groups[gi])
        if len(test_dates) < min_fold_n:
            continue
        active_oc: list[str] = []
        shadow_oc: list[str] = []
        for dk in test_dates:
            d = day_by[dk]
            active_oc.append(d["arms"]["active_locked"]["outcome"])
            shadow_oc.append(d["arms"][arm_id]["outcome"])
        active_m = _metrics_from_outcomes(active_oc)
        shadow_m = _metrics_from_outcomes(shadow_oc)
        a_soft = float(active_m.get("soft_hit_rate") or 0)
        s_soft = float(shadow_m.get("soft_hit_rate") or 0)
        delta = round(s_soft - a_soft, 4)
        deltas.append(delta)
        folds.append(
            {
                "fold_id": f"G{'-'.join(str(i + 1) for i in test_idx)}",
                "test_group_indices": list(test_idx),
                "n_test_days": len(test_dates),
                "test_date_from": test_dates[0],
                "test_date_to": test_dates[-1],
                "active": active_m,
                "shadow": shadow_m,
                "soft_delta_shadow_minus_active": delta,
            }
        )

    full_active = float((bundle.get("summary") or {}).get("active_locked", {}).get("soft_hit_rate") or 0)
    full_shadow = float((bundle.get("summary") or {}).get(arm_id, {}).get("soft_hit_rate") or 0)
    pos = sum(1 for d in deltas if d > 0)
    n_folds = len(deltas)
    median_delta = sorted(deltas)[n_folds // 2] if deltas else None

    gate_pass = bool(
        n_folds >= 5
        and pos / n_folds >= 0.6
        and median_delta is not None
        and median_delta >= 0.03
    )

    return {
        "schema": "kospi_cpcv_shadow_promotion_poc_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "arm_id": arm_id,
        "as_of_kst": as_of_kst,
        "n_groups": n_groups,
        "n_test_groups": n_test_groups,
        "n_scored_days_full": len(scored_dates),
        "merged_months": calendar.get("merged_from"),
        "full_sample": {
            "active_soft_hit_rate": full_active,
            "shadow_soft_hit_rate": full_shadow,
            "soft_delta_pp": round((full_shadow - full_active) * 100, 2),
        },
        "cpcv_folds": folds,
        "fold_summary": {
            "n_folds": n_folds,
            "n_positive_delta": pos,
            "positive_rate": round(pos / n_folds, 4) if n_folds else None,
            "median_soft_delta": median_delta,
            "min_soft_delta": min(deltas) if deltas else None,
            "max_soft_delta": max(deltas) if deltas else None,
            "mean_soft_delta": round(sum(deltas) / n_folds, 4) if n_folds else None,
        },
        "promotion_poc_gate": {
            "min_folds": 5,
            "min_positive_rate": 0.6,
            "min_median_soft_delta": 0.03,
            "pass": gate_pass,
            "verdict_ko": (
                "CPCV PoC 통과 — July OOS 누적 후 human signoff 검토 가능"
                if gate_pass
                else "CPCV PoC 미통과 — composite June·merged 과적합 의심, apply 금지"
            ),
        },
        "lit_review": "docs/research/KOSPI_REGIME_SWITCH_CPCV_LIT_REVIEW_2026-06-26.md",
        "reproduce": (
            "py scripts/build_kospi_cpcv_shadow_promotion_poc_v1.py "
            f"--as-of-kst {as_of_kst} --n-groups {n_groups} --n-test-groups {n_test_groups}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of-kst", default="2026-06-26")
    ap.add_argument("--n-groups", type=int, default=6)
    ap.add_argument("--n-test-groups", type=int, default=2)
    ap.add_argument("--arm-id", default="composite_bear_conditional")
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--hero-calendar", type=Path, default=DEFAULT_HERO)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    calendar = merge_calendars(MERGE_MONTHS_DEFAULT)
    if not calendar.get("rows"):
        print(json.dumps({"ok": False, "error": "no_merged_calendar_rows"}, ensure_ascii=False))
        return 1

    eval_doc = eval_calendar(calendar, as_of_kst=ns.as_of_kst)
    rules = _read(ns.rules_json)
    from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _load_flow

    flow = _load_flow(DEFAULT_FLOW)
    hero_cal = _read(ns.hero_calendar)

    doc = build_cpcv_poc(
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        flow=flow,
        hero_cal=hero_cal,
        as_of_kst=ns.as_of_kst,
        n_groups=ns.n_groups,
        n_test_groups=ns.n_test_groups,
        arm_id=ns.arm_id,
    )
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_cpcv_shadow_promotion_poc_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate = (doc.get("promotion_poc_gate") or {}).get("pass")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(ns.output),
                "n_folds": (doc.get("fold_summary") or {}).get("n_folds"),
                "promotion_poc_gate_pass": gate,
                "median_delta": (doc.get("fold_summary") or {}).get("median_soft_delta"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
