#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monthly KOSPI forward outlook 2026–2028 from v2 calendar + composite shadow [HYPO].

Outputs direction + illustrative index band (not price oracle). research_only · send_gate HOLD.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _coord_raw_bull  # noqa: E402
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
)
from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import (  # noqa: E402
    _load_closes,
    _panel_csv_for_month,
    _run_panel,
    build_calendar,
)
from scripts.kospi_composite_shadow_lib_v1 import composite_bear_conditional as composite_direction  # noqa: E402
from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_OUT = ROOT / "reports/kospi_monthly_forward_outlook_2026_2028_v1_latest.json"
DEFAULT_MD = ROOT / "reports/kospi_monthly_forward_outlook_2026_2028_v1_latest.md"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

DIR_KO = {"bull": "상승", "bear": "하락", "neutral": "횡보·관측"}


def _utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _month_range(year_from: int, year_to: int) -> list[str]:
    out: list[str] = []
    for y in range(year_from, year_to + 1):
        for m in range(1, 13):
            out.append(f"{y:04d}-{m:02d}")
    return out


def _majority_direction(directions: list[str]) -> str:
    if not directions:
        return "neutral"
    counts = {"bull": 0, "bear": 0, "neutral": 0}
    for d in directions:
        counts[str(d).lower()] = counts.get(str(d).lower(), 0) + 1
    winner = max(counts, key=lambda k: counts[k])
    top = counts[winner]
    if sum(1 for c in counts.values() if c == top) > 1:
        return "neutral"
    return winner


def _mid_pct(cal_row: dict[str, Any], direction: str, detail: dict[str, Any] | None = None) -> float:
    if detail and detail.get("blended_score") is not None:
        return float(detail["blended_score"]) * 0.8
    band = cal_row.get("kospi_index_prophecy") if isinstance(cal_row.get("kospi_index_prophecy"), dict) else {}
    if band.get("predicted_return_mid_pct") is not None:
        return float(band["predicted_return_mid_pct"])
    return {"bull": 0.45, "bear": -0.45, "neutral": 0.0}.get(direction, 0.0)


def _ensure_calendar(ym: str, *, write: bool) -> dict[str, Any]:
    tag = ym.replace("-", "")
    path = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    panel = _panel_csv_for_month(ym)
    if not panel.is_file():
        y, m = map(int, ym.split("-"))
        start = date(y, m, 1)
        end = date(y, 12, 31) if m == 12 else date(y, m + 1, 1)
        from datetime import timedelta

        end = end - timedelta(days=1)
        from scripts.kospi_krx_calendar_v1 import krx_trading_days

        days = krx_trading_days(start, end)
        if days:
            _run_panel(days, panel)
    if path.is_file() and not write:
        return _read(path)
    doc = build_calendar(year_month=ym, skip_panel=True, profile="v2_multilens")
    if write:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def _composite_for_row(
    cal_row: dict[str, Any],
    *,
    rules: dict[str, Any],
    flow: dict[str, float | None],
    eval_stub: dict[str, Any],
) -> tuple[str, str, str, dict[str, Any]]:
    dk = str(cal_row.get("session_date"))
    active = str(cal_row.get("predicted_direction") or "neutral")
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    bear_triple, bear_detail, _ = replay_scenario(
        cal_row,
        scenario_id=BEAR_SCENARIO,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    coord_raw, coord_mode = _coord_raw_bull(cal_row, rules, eval_stub)
    prior_ctx = resolve_prior_foreign_for_gate(
        flow, dk, max_lag_calendar_days=max_lag_from_rules(rules)
    )
    prior_fn = prior_ctx.value
    shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
    allow_unlock, blocks = evaluate_conditional_unlock(
        prior_foreign=prior_fn,
        shock_pred=shock_pred,
        foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
        apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
    )
    if prior_ctx.gate_mode == "skipped_stale_forward":
        blocks = list(blocks) + ["flow_gate_skipped_stale_forward"]
    unlock_candidate = active == "neutral" and coord_raw == "bull"
    composite_dir = composite_direction(
        v2=active,
        bear_triple=bear_triple,
        coord_raw=coord_raw,
        unlock_candidate=unlock_candidate,
        cond_allow=allow_unlock,
    )
    meta = {
        "unlock_candidate": unlock_candidate,
        "conditional_blocks": blocks,
        "coordinator_raw": coord_raw,
        "coordinator_resolution_mode": coord_mode,
    }
    return active, bear_triple, composite_dir, {"bear_detail": bear_detail, **meta}


def build_outlook(
    *,
    year_from: int = 2026,
    year_to: int = 2028,
    write_calendars: bool = False,
) -> dict[str, Any]:
    rules = _read(DEFAULT_RULES)
    flow = load_flow_daily(ROOT / "research/market_data/kospi_daily_flow_external.csv")
    real_closes = _load_closes(KOSPI_CSV)
    eval_stub: dict[str, Any] = {"rows": []}

    sim_close = max(real_closes.values()) if real_closes else None
    last_real_date = max(real_closes) if real_closes else None
    anchor_ym = last_real_date[:7] if last_real_date else None

    months_out: list[dict[str, Any]] = []

    for ym in _month_range(year_from, year_to):
        cal = _ensure_calendar(ym, write=write_calendars)
        rows = cal.get("rows") or []
        if not rows:
            continue

        active_dirs: list[str] = []
        composite_dirs: list[str] = []
        active_mids: list[float] = []
        composite_mids: list[float] = []

        first_dk = str(rows[0].get("session_date"))
        last_dk = str(rows[-1].get("session_date"))
        use_forward_chain = anchor_ym is not None and ym > anchor_ym
        if use_forward_chain and sim_close is not None:
            month_start_close = sim_close
        else:
            month_start_close = real_closes.get(first_dk)
            if month_start_close is None and sim_close is not None:
                month_start_close = sim_close
            elif month_start_close is not None and not use_forward_chain:
                sim_close = month_start_close

        for cal_row in rows:
            active, bear_triple, composite_dir, meta = _composite_for_row(
                cal_row, rules=rules, flow=flow, eval_stub=eval_stub
            )
            active_dirs.append(active)
            composite_dirs.append(composite_dir)
            active_mids.append(_mid_pct(cal_row, active))
            bear_detail = meta.get("bear_detail") if isinstance(meta.get("bear_detail"), dict) else {}
            composite_mids.append(
                _mid_pct(cal_row, composite_dir, bear_detail if composite_dir == bear_triple else None)
            )

        month_end_close_active = month_start_close
        month_end_close_composite = month_start_close
        if month_start_close:
            c_a = float(month_start_close)
            c_c = float(month_start_close)
            for mid in active_mids:
                c_a *= 1.0 + mid / 100.0
            for mid in composite_mids:
                c_c *= 1.0 + mid / 100.0
            month_end_close_active = round(c_a, 1)
            month_end_close_composite = round(c_c, 1)
            sim_close = month_end_close_composite

        active_month_dir = _majority_direction(active_dirs)
        composite_month_dir = _majority_direction(composite_dirs)
        month_return_active = (
            round((month_end_close_active / month_start_close - 1) * 100, 2)
            if month_start_close and month_end_close_active
            else None
        )
        month_return_composite = (
            round((month_end_close_composite / month_start_close - 1) * 100, 2)
            if month_start_close and month_end_close_composite
            else None
        )

        is_future = last_real_date is not None and first_dk > last_real_date
        is_partial = last_real_date is not None and last_dk > last_real_date >= first_dk
        if anchor_ym and ym == anchor_ym and last_real_date in real_closes:
            sim_close = real_closes[last_real_date]

        months_out.append(
            {
                "year_month": ym,
                "n_trading_days": len(rows),
                "data_mode": (
                    "forward_sim"
                    if use_forward_chain
                    else ("partial_real" if is_partial else "calendar_blend")
                ),
                "month_start_close": round(month_start_close, 2) if month_start_close else None,
                "active": {
                    "month_direction": active_month_dir,
                    "month_direction_ko": DIR_KO.get(active_month_dir, active_month_dir),
                    "bull_days": active_dirs.count("bull"),
                    "bear_days": active_dirs.count("bear"),
                    "neutral_days": active_dirs.count("neutral"),
                    "implied_month_end_close": month_end_close_active,
                    "implied_month_return_pct": month_return_active,
                },
                "composite_shadow": {
                    "month_direction": composite_month_dir,
                    "month_direction_ko": DIR_KO.get(composite_month_dir, composite_month_dir),
                    "bull_days": composite_dirs.count("bull"),
                    "bear_days": composite_dirs.count("bear"),
                    "neutral_days": composite_dirs.count("neutral"),
                    "implied_month_end_close": month_end_close_composite,
                    "implied_month_return_pct": month_return_composite,
                    "commander_signoff_arm": True,
                },
            }
        )

    return {
        "schema": "kospi_monthly_forward_outlook_2026_2028_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_live": False,
        "long_horizon_headline_excluded": True,
        "long_horizon_headline_note_ko": "2027-2028 outlook·지수 복리는 승격·3줄 headline 제외 — July OOS + June CPCV만",
        "disclaimer_ko": (
            "방향·지수 밴드는 B-track [HYPO] 참고용. composite=지휘관 shadow 승인 arm. "
            "실제 지수 예언·투자 판단 아님. 2026-06-26 이후 구간은 시뮬레이션 체인."
        ),
        "method_ko": {
            "daily": "v2_multilens 캘린더 + composite_bear_conditional (bear_triple / 조건부 4AI)",
            "monthly_direction": "거래일 방향 다수결",
            "monthly_index": "일별 mid 수익률 복리 시뮬 (blended_score×0.8 또는 방향 기본값)",
        },
        "anchor_close_real": round(real_closes[last_real_date], 2) if last_real_date else None,
        "anchor_date": last_real_date,
        "year_from": year_from,
        "year_to": year_to,
        "months": months_out,
        "reproduce": (
            f"py scripts/build_kospi_monthly_forward_outlook_v1.py --year-from {year_from} --year-to {year_to}"
        ),
    }


def _render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# KOSPI 월별 전망 2026–2028 [HYPO · research_only]",
        "",
        f"- 생성: `{doc.get('generated_at_utc')}` · send_gate: **HOLD**",
        f"- 앵커 실종가: **{doc.get('anchor_close_real')}** ({doc.get('anchor_date')})",
        f"- 방법: v2 3렌즈 blend + **composite_bear_conditional** shadow (지휘관 승인)",
        "",
        "> 지수 구간은 일별 mid 복리 **시뮬**이며 실제 예언이 아닙니다.",
        "",
        "| 월 | composite 방향 | composite 월말(시뮬) | 월수익% | active 방향 | 비고 |",
        "|---|----------------|---------------------|--------|------------|------|",
    ]
    for m in doc.get("months") or []:
        cs = m.get("composite_shadow") or {}
        ac = m.get("active") or {}
        lines.append(
            "| {ym} | {cd} | {end} | {ret} | {ad} | {mode} |".format(
                ym=m.get("year_month"),
                cd=cs.get("month_direction_ko"),
                end=cs.get("implied_month_end_close") or "—",
                ret=cs.get("implied_month_return_pct") if cs.get("implied_month_return_pct") is not None else "—",
                ad=ac.get("month_direction_ko"),
                mode=m.get("data_mode"),
            )
        )
    lines.extend(["", f"재현: `{doc.get('reproduce')}`", ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-from", type=int, default=2026)
    ap.add_argument("--year-to", type=int, default=2028)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    ap.add_argument("--write-calendars", action="store_true")
    ns = ap.parse_args()

    doc = build_outlook(year_from=ns.year_from, year_to=ns.year_to, write_calendars=ns.write_calendars)
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_monthly_forward_outlook_2026_2028_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ns.markdown.write_text(_render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "n_months": len(doc.get("months") or []), "out": str(ns.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
