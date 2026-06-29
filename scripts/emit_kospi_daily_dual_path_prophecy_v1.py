#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit single-session dual_path_v2 prophecy card from monthly shadow artifact [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SHADOW = ROOT / "reports/kospi_dual_path_conflict_shadow_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_daily_dual_path_prophecy_latest.json"
DEFAULT_LOG = ROOT / "reports/kospi_daily_dual_path_prophecy_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_session_date(session_date: str | None) -> tuple[str, str]:
    from scripts.kospi_krx_calendar_v1 import (
        krx_trading_days,
        last_krx_trading_day_on_or_before,
        next_krx_trading_day_on_or_after,
    )

    today = date.today()
    if session_date:
        return session_date[:10], "explicit"
    last_sess = last_krx_trading_day_on_or_before(today)
    if last_sess and last_sess in set(krx_trading_days(today, today)):
        return last_sess, "today_trading"
    nxt = next_krx_trading_day_on_or_after(today)
    if nxt:
        return nxt, "next_session_prep"
    return (last_sess or today.isoformat()), "fallback_last_session"


def emit_card(
    *,
    shadow_doc: dict[str, Any],
    session_date: str,
    data_mode: str,
    eval_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    day_row = next(
        (d for d in (shadow_doc.get("days") or []) if str(d.get("session_date")) == session_date[:10]),
        None,
    )
    if not day_row:
        return {
            "schema": "kospi_daily_dual_path_prophecy_v1",
            "generated_at_utc": _utc(),
            "hypothesis_tier": "B",
            "research_only": True,
            "send_gate": "HOLD",
            "auto_apply": False,
            "session_date": session_date,
            "data_mode": data_mode,
            "status": "missing_shadow_row",
            "note_ko": "월간 shadow 재빌드 후 재시도",
        }

    arms = day_row.get("arms") or {}
    v2 = arms.get("dual_path_v2_router") or {}
    active = arms.get("active_locked") or {}
    actual = day_row.get("actual_direction")
    if eval_doc:
        er = next(
            (r for r in (eval_doc.get("rows") or []) if str(r.get("session_date")) == session_date[:10]),
            None,
        )
        if er:
            actual = er.get("actual_direction") or actual

    return {
        "schema": "kospi_daily_dual_path_prophecy_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "production_apply_authorized": False,
        "session_date": session_date,
        "data_mode": data_mode,
        "scoring_arm": "dual_path_v2_router",
        "predicted_direction": v2.get("direction"),
        "predicted_outcome": v2.get("outcome"),
        "active_direction": active.get("direction"),
        "active_outcome": active.get("outcome"),
        "actual_direction": actual,
        "dual_path_v2_route": day_row.get("dual_path_v2_route"),
        "tier_a_apply": day_row.get("tier_a_apply"),
        "tier_b_detected": day_row.get("tier_b_detected"),
        "conflict_detected": day_row.get("conflict_detected"),
        "meta": day_row.get("meta"),
        "insight_ko": _insight_line(day_row, actual),
        "reproduce": (
            f"py scripts/build_kospi_dual_path_conflict_shadow_v1.py "
            f"--year-month {session_date[:7]} --as-of-kst {session_date}"
        ),
    }


def _insight_line(day_row: dict[str, Any], actual: str | None) -> str:
    route = day_row.get("dual_path_v2_route") or "baseline"
    v2 = ((day_row.get("arms") or {}).get("dual_path_v2_router") or {}).get("direction")
    oc = ((day_row.get("arms") or {}).get("dual_path_v2_router") or {}).get("outcome")
    if not actual:
        return f"예측={v2} route={route} — 장 마감 후 채점"
    if oc == "HIT":
        return f"적중 route={route} (v2={v2} actual={actual})"
    if oc == "NEUTRAL_DRAW":
        return f"중립 draw route={route}"
    return f"FAIL route={route} v2={v2} actual={actual} — evening miss insight 참고"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", default=None)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--eval-json", type=Path, default=None)
    ap.add_argument("--data-mode", default=None, choices=("today_trading", "next_session_prep", "evening_score", "explicit"))
    ap.add_argument("--append-log", action="store_true", default=True)
    ap.add_argument("--no-append-log", action="store_false", dest="append_log")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    session, inferred_mode = _resolve_session_date(ns.session_date)
    data_mode = ns.data_mode or inferred_mode
    shadow = _read(ns.shadow_json if ns.shadow_json.is_absolute() else ROOT / ns.shadow_json)
    eval_doc = None
    if ns.eval_json:
        eval_doc = _read(ns.eval_json if ns.eval_json.is_absolute() else ROOT / ns.eval_json)
    elif data_mode == "evening_score":
        tag = session.replace("-", "")[:6]
        for p in (
            ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json",
            ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ):
            if p.is_file():
                eval_doc = _read(p)
                break

    card = emit_card(
        shadow_doc=shadow,
        session_date=session,
        data_mode=data_mode,
        eval_doc=eval_doc,
    )
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_daily_dual_path_prophecy_latest.json"
    art.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if ns.append_log:
        DEFAULT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DEFAULT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": card.get("status") != "missing_shadow_row",
                "session_date": session,
                "data_mode": data_mode,
                "predicted": card.get("predicted_direction"),
                "outcome": card.get("predicted_outcome"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if card.get("status") != "missing_shadow_row" else 1


if __name__ == "__main__":
    raise SystemExit(main())
