#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-session KOSPI weight counterfactual [HYPO][research_only]."""

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

from scripts.kospi_weight_counterfactual_lib_v1 import (  # noqa: E402
    WEIGHT_SCENARIOS,
    build_session_weight_counterfactual,
)

EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_weight_counterfactual_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path]:
    tag = year_month.replace("-", "")
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if year_month == "2026-06" and not ev.is_file():
        ev = DEFAULT_EVAL
    out = ROOT / f"reports/kospi_{tag}_weight_counterfactual_v1_latest.json"
    return cal, ev, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", default=None, help="YYYY-MM-DD; default last FAIL in eval")
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar", type=Path, default=None)
    ap.add_argument("--eval", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all-fails", action="store_true", help="Build for all active FAIL days in month")
    args = ap.parse_args()

    cal_p, ev_p, month_out = _paths_for_month(args.year_month)
    cal_p = args.calendar or cal_p
    ev_p = args.eval or ev_p
    if not cal_p.is_absolute():
        cal_p = ROOT / cal_p
    if not ev_p.is_absolute():
        ev_p = ROOT / ev_p
    out_p = args.output if args.output.is_absolute() else ROOT / args.output
    if args.output == DEFAULT_OUT and args.year_month != "2026-06":
        out_p = month_out

    cal = _read_json(cal_p)
    ev = _read_json(ev_p)
    rules = _read_json(args.rules_json if args.rules_json.is_absolute() else ROOT / args.rules_json)
    cal_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (cal.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }

    targets: list[dict[str, Any]] = []
    for er in ev.get("rows") or []:
        if not isinstance(er, dict):
            continue
        dk = str(er.get("session_date") or "")[:10]
        if args.session_date and dk != args.session_date[:10]:
            continue
        if args.all_fails and er.get("outcome") != "FAIL":
            continue
        if not args.session_date and not args.all_fails:
            continue
        targets.append(er)

    if not targets and not args.all_fails:
        fails = [r for r in (ev.get("rows") or []) if isinstance(r, dict) and r.get("outcome") == "FAIL"]
        if fails:
            targets = [fails[-1]]
        elif args.session_date:
            targets = [r for r in (ev.get("rows") or []) if str(r.get("session_date")) == args.session_date[:10]]

    if not targets:
        print(json.dumps({"ok": False, "error": "no_target_sessions"}, ensure_ascii=False))
        return 1

    docs: list[dict[str, Any]] = []
    for er in targets:
        dk = str(er.get("session_date") or "")[:10]
        cal_row = cal_by.get(dk)
        if not cal_row:
            continue
        docs.append(
            build_session_weight_counterfactual(
                session_date=dk,
                cal_row=cal_row,
                actual_direction=str(er.get("actual_direction") or "neutral"),
                active_direction=str(er.get("predicted_direction") or "neutral"),
                scenario_ids=list(WEIGHT_SCENARIOS.keys()),
                rules=rules,
            )
        )

    if len(docs) == 1:
        doc = docs[0]
    else:
        doc = {
            "schema": "kospi_june2026_weight_counterfactual_batch_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "send_gate": "HOLD",
            "year_month": args.year_month,
            "n_sessions": len(docs),
            "sessions": docs,
        }
    doc["generated_at_utc"] = _utc_now()
    doc["inputs"] = {
        "calendar_path": str(cal_p).replace("\\", "/"),
        "eval_path": str(ev_p).replace("\\", "/"),
        "n_scenarios": len(WEIGHT_SCENARIOS),
    }

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if out_p != DEFAULT_OUT and args.year_month == "2026-06":
        DEFAULT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(out_p), "n_sessions": len(docs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
