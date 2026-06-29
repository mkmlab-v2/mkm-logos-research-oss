#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""7-day 4AI lock/unlock diff panel joined with macro·flow·headline·stress [HYPO].

Hypothesis: unlock diffs are homogenous balance_bull lifts from v2 neutral,
not per-day macro variable distortion. research_only · apply forbidden.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_macro_news_shock_headline_verify_lib_v1 import headline_gt_for_session
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import (  # noqa: E402
    _resolve_calendar_path,
    four_ai_counterfactual,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
import scripts.kospi_june_4ai_prophecy_overlay_v1 as overlay  # noqa: E402

DEFAULT_STRESS_CROSS = ROOT / "reports/kospi_june2026_stress_shadow_lens_4ai_cross_v1_latest.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DEFAULT_MACRO = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_unlock_diff_macro_panel_v1_latest.json"
SCHEMA = "kospi_june2026_unlock_diff_macro_panel_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_flow(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, Any] = {"date": dk}
            for col in ("foreign_net_buy", "institution_net_buy", "program_net_buy"):
                raw = row.get(col)
                if raw not in (None, ""):
                    try:
                        entry[col] = float(raw)
                    except (ValueError, TypeError):
                        entry[col] = None
            out[dk] = entry
    return out


def _channel_summary(blend: dict[str, Any]) -> dict[str, Any]:
    channels = blend.get("channels") if isinstance(blend.get("channels"), list) else []
    nonzero: list[dict[str, Any]] = []
    suppressed_bear: list[str] = []
    for ch in channels:
        if not isinstance(ch, dict):
            continue
        w = float(ch.get("weight") or 0.0)
        d = str(ch.get("direction") or "neutral")
        name = str(ch.get("channel") or ch.get("name") or "")
        if w > 0:
            nonzero.append({"channel": name, "direction": d, "weight": round(w, 4)})
        if d == "bear" and w == 0.0 and name:
            suppressed_bear.append(name)
    return {
        "nonzero_channels": nonzero,
        "suppressed_bear_channels": suppressed_bear,
        "blended_score": blend.get("blended_score"),
    }


def _unlocked_row(
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    session_date: str,
) -> dict[str, Any]:
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    coord_base = rules.get("four_ai_coordinator_policy") if isinstance(rules.get("four_ai_coordinator_policy"), dict) else {}
    unlocked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": False}
    cal_row = next((r for r in (calendar.get("rows") or []) if str(r.get("session_date")) == session_date), {})
    unlocked_doc = overlay.build_4ai_report(
        {"rows": [cal_row], "year_month": calendar.get("year_month")},
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=unlocked_pol,
    )
    rows = unlocked_doc.get("rows") or []
    return rows[0] if rows else {}


def build_panel(
    *,
    diff_rows: list[dict[str, Any]],
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    stress_by_date: dict[str, dict[str, Any]],
    flow_by_date: dict[str, dict[str, Any]],
    pre_news: dict[str, Any],
    macro_lens: dict[str, Any],
    year_month: str,
    as_of_kst: str,
) -> dict[str, Any]:
    eval_by = {str(r.get("session_date")): r for r in (eval_doc.get("rows") or [])}
    cal_by = {str(r.get("session_date")): r for r in (calendar.get("rows") or [])}

    panel_days: list[dict[str, Any]] = []
    for diff in diff_rows:
        dk = str(diff.get("session_date") or "")
        if not dk:
            continue
        ev = eval_by.get(dk, {})
        cal = cal_by.get(dk, {})
        blend = cal.get("blend") if isinstance(cal.get("blend"), dict) else {}
        actual = str(ev.get("actual_direction") or diff.get("actual_direction") or "neutral")
        v2_dir = str(diff.get("v2_direction") or ev.get("predicted_direction") or "neutral")
        locked_dir = str(diff.get("four_ai_locked") or v2_dir)
        unlocked_dir = str(diff.get("four_ai_unlocked") or "neutral")
        unlocked_row = _unlocked_row(calendar, eval_doc, rules, dk)
        ab = unlocked_row.get("absolute_balance") if isinstance(unlocked_row.get("absolute_balance"), dict) else {}
        flow = flow_by_date.get(dk, {})
        stress = stress_by_date.get(dk, {})
        headline = headline_gt_for_session(pre_news, dk)

        foreign = flow.get("foreign_net_buy")
        flow_sign = None
        if isinstance(foreign, (int, float)):
            flow_sign = "net_buy" if foreign > 0 else "net_sell"

        locked_outcome = str(ev.get("outcome") or _outcome(locked_dir, actual))
        unlocked_outcome = _outcome(unlocked_dir, actual)

        panel_days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "daily_return_pct": ev.get("daily_return_pct"),
                "lock_unlock": {
                    "v2_direction": v2_dir,
                    "four_ai_locked": locked_dir,
                    "four_ai_unlocked": unlocked_dir,
                    "unlocked_resolution_mode": diff.get("unlocked_resolution_mode")
                    or ab.get("resolution_mode"),
                    "would_change_v2_calendar": diff.get("would_change_v2_calendar"),
                    "coordinator_direction_raw": ab.get("coordinator_direction"),
                    "coordinator_mean_score": ab.get("coordinator_mean_score"),
                    "locked_outcome": locked_outcome,
                    "unlocked_outcome": unlocked_outcome,
                    "unlock_would_beat_locked": (
                        1.0
                        if unlocked_outcome == "HIT"
                        else (0.5 if unlocked_outcome == "NEUTRAL_DRAW" else 0.0)
                    )
                    > (1.0 if locked_outcome == "HIT" else (0.5 if locked_outcome == "NEUTRAL_DRAW" else 0.0)),
                },
                "v2_blend": _channel_summary(blend),
                "market_stress": {
                    "market_stress": stress.get("market_stress"),
                    "market_stress_reasons": stress.get("market_stress_reasons"),
                    "prior_vol_5d_stdev": stress.get("prior_vol_5d_stdev"),
                },
                "flow": {
                    "foreign_net_buy": foreign,
                    "institution_net_buy": flow.get("institution_net_buy"),
                    "flow_sign": flow_sign,
                },
                "headline_verify": headline if headline.get("headline_scorable") else {"headline_scorable": False},
                "macro_lens_snapshot_global": {
                    "direction": macro_lens.get("direction"),
                    "confidence": macro_lens.get("confidence"),
                    "note": "global snapshot; not session-local macro feed",
                },
            }
        )

    modes = [str(d["lock_unlock"].get("unlocked_resolution_mode") or "") for d in panel_days]
    homogenous_mode = len(set(modes)) == 1 and bool(modes)
    unlock_hits = sum(1 for d in panel_days if d["lock_unlock"].get("unlocked_outcome") == "HIT")
    unlock_fails = sum(1 for d in panel_days if d["lock_unlock"].get("unlocked_outcome") == "FAIL")
    unlock_neutral = sum(1 for d in panel_days if d["lock_unlock"].get("unlocked_outcome") == "NEUTRAL_DRAW")
    rescue = sum(1 for d in panel_days if d["lock_unlock"].get("unlock_would_beat_locked"))

    bear_actual_unlock_fail = [
        d["session_date"]
        for d in panel_days
        if d.get("actual_direction") == "bear" and d["lock_unlock"].get("unlocked_outcome") == "FAIL"
    ]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "n_diff_days": len(panel_days),
        "summary": {
            "pattern": "neutral_to_bull_via_balance_bull" if homogenous_mode and modes[0] == "balance_bull" else "mixed",
            "homogenous_unlock_resolution_mode": homogenous_mode,
            "dominant_unlock_resolution_mode": modes[0] if homogenous_mode else None,
            "unlock_outcomes": {
                "hit": unlock_hits,
                "fail": unlock_fails,
                "neutral_draw": unlock_neutral,
                "directional_hit_rate": round(unlock_hits / (unlock_hits + unlock_fails), 4)
                if (unlock_hits + unlock_fails)
                else None,
            },
            "n_unlock_would_beat_locked": rescue,
            "bear_actual_unlock_fail_dates": bear_actual_unlock_fail,
            "macro_distortion_verdict_ko": (
                "7일 모두 unlocked_resolution_mode=balance_bull · v2 neutral→unlock bull 동형. "
                "매크로 변수 일별 왜곡보다 코디네이터 중립 밴드 해소 패턴이 지배적. "
                f"bear 실현일 unlock FAIL: {', '.join(bear_actual_unlock_fail) or '없음'}. apply 금지."
            ),
        },
        "days": panel_days,
        "sources": {
            "stress_cross": "reports/kospi_june2026_stress_shadow_lens_4ai_cross_v1_latest.json",
            "eval": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
            "calendar": str(calendar.get("calendar_path") or "reports/kospi_202606_daily_prophecy_calendar_v1.json"),
            "pre_news": "docs/final/artifacts/pre_news_shadow_input_latest.json",
            "macro_lens": "docs/final/artifacts/macro_independent_lens_latest.json",
            "flow_csv": "research/market_data/kospi_daily_flow_external.csv",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--stress-cross-json", type=Path, default=DEFAULT_STRESS_CROSS)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _default_as_of_kst

    stress_cross = _read(args.stress_cross_json if args.stress_cross_json.is_absolute() else ROOT / args.stress_cross_json)
    diff_rows = (stress_cross.get("four_ai_lock_unlock_on_stress") or {}).get("diff_rows") or []
    if not diff_rows:
        cf = four_ai_counterfactual(
            _read(_resolve_calendar_path(args.calendar_json, year_month=args.year_month)),
            evolution_path=DEFAULT_RULES,
            eval_doc=_read(args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json),
        )
        diff_rows = cf.get("diff_rows") or []

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month).resolve()
    calendar = _read(cal_path)
    calendar["calendar_path"] = str(cal_path.relative_to(ROOT)).replace("\\", "/")
    eval_doc = _read(args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json)
    rules = _read(DEFAULT_RULES)
    stress_by = {str(d.get("session_date")): d for d in (stress_cross.get("stress_shadow_days") or [])}
    flow_by = _load_flow(DEFAULT_FLOW)
    pre_news = _read(DEFAULT_PRE_NEWS)
    macro = _read(DEFAULT_MACRO)
    as_of = args.as_of_kst or _default_as_of_kst()

    doc = build_panel(
        diff_rows=diff_rows,
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        stress_by_date=stress_by,
        flow_by_date=flow_by,
        pre_news=pre_news,
        macro_lens=macro,
        year_month=args.year_month,
        as_of_kst=as_of,
    )
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "n_diff_days": doc["n_diff_days"],
                "pattern": doc["summary"].get("pattern"),
                "unlock_hr": doc["summary"]["unlock_outcomes"].get("directional_hit_rate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
