#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build hero shock_gate shadow panel vs active kospi_direction [HYPO][research_only]."""

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

from scripts.kospi_hero_shock_gate_shadow_lib_v1 import (  # noqa: E402
    aggregate_shadow_days,
    resolve_policy,
    score_shadow_day,
)

EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_KOSPI_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_HERO_CAL = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_hero_shock_gate_shadow_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_hero_shock_gate_shadow_v1_latest.json"
DEFAULT_LOG = ROOT / "reports/kospi_hero_shock_gate_shadow_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path]:
    tag = year_month.replace("-", "")
    eval_candidates = [
        ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json" if year_month == "2026-06" else None,
    ]
    eval_path = next((p for p in eval_candidates if p and p.is_file()), eval_candidates[0])
    return (
        eval_path,
        ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json",
        ROOT / f"reports/kospi_hero_shock_gate_shadow_{tag}_v1_latest.json",
    )


def build_shadow_panel(
    *,
    kospi_eval: dict[str, Any],
    hero_cal: dict[str, Any],
    rules: dict[str, Any],
    as_of_kst: str | None = None,
    year_month: str | None = None,
) -> dict[str, Any]:
    policy = resolve_policy(rules)
    eval_rows = [r for r in (kospi_eval.get("rows") or []) if isinstance(r, dict)]
    if as_of_kst:
        eval_rows = [r for r in eval_rows if str(r.get("session_date") or "") <= as_of_kst[:10]]

    hero_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (hero_cal.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }

    days: list[dict[str, Any]] = []
    for er in eval_rows:
        dk = str(er.get("session_date") or "")[:10]
        if not dk:
            continue
        hero_row = hero_by.get(dk) or {}
        shock_pred = ((hero_row.get("slots") or {}).get("macro_news_shock") or {})
        foreign_pred = ((hero_row.get("slots") or {}).get("foreign_flow") or {})
        days.append(
            score_shadow_day(
                session_date=dk,
                active_direction=str(er.get("predicted_direction") or "neutral"),
                actual_direction=str(er.get("actual_direction") or "neutral"),
                shock_pred=shock_pred,
                foreign_flow_pred=foreign_pred,
                policy=policy,
            )
        )

    ym = year_month or kospi_eval.get("year_month") or hero_cal.get("year_month")
    agg = aggregate_shadow_days(days)
    oos_start = str(policy.get("oos_forward_start") or "2026-07-01")
    oos_days = [d for d in days if str(d.get("session_date") or "") >= oos_start]
    june_days = [d for d in days if str(d.get("session_date") or "").startswith("2026-06")]

    return {
        "schema": "kospi_hero_shock_gate_shadow_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": ym,
        "as_of_kst": as_of_kst,
        "policy": policy,
        "inputs": {
            "kospi_eval_year_month": kospi_eval.get("year_month"),
            "hero_calendar_year_month": hero_cal.get("year_month"),
            "n_eval_rows": len(eval_rows),
            "n_hero_rows": len(hero_by),
        },
        "aggregate": agg,
        "june_subset": aggregate_shadow_days(june_days) if june_days else None,
        "oos_forward_subset": aggregate_shadow_days(oos_days) if oos_days else None,
        "days": days,
        "verdict_ko": (
            f"shadow soft {agg['shadow'].get('soft_hit_rate')} vs active {agg['active'].get('soft_hit_rate')} "
            f"(Δ {agg.get('shadow_minus_active_soft_pp')}pp, gate_applied={agg.get('n_gate_applied')}). apply 금지."
        ),
    }


def append_log_line(doc: dict[str, Any], log_path: Path) -> None:
    last = (doc.get("days") or [])[-1] if doc.get("days") else None
    if not last:
        return
    line = {
        "schema": "kospi_hero_shock_gate_shadow_log_v1",
        "ts_utc": doc.get("generated_at_utc"),
        "session_date": last.get("session_date"),
        "active_outcome": last.get("active_outcome"),
        "shadow_outcome": last.get("shadow_outcome"),
        "gate_applied": last.get("gate_applied"),
        "softened_active_fail": last.get("softened_active_fail"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--kospi-eval", type=Path, default=None)
    ap.add_argument("--hero-calendar", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--log-path", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    ym = args.year_month
    kospi_eval_path = args.kospi_eval
    hero_cal_path = args.hero_calendar
    out_path = args.output

    if ym:
        ev_p, _, month_out = _paths_for_month(ym)
        kospi_eval_path = kospi_eval_path or ev_p
        hero_cal_path = hero_cal_path or DEFAULT_HERO_CAL
        if args.output == DEFAULT_OUT:
            out_path = month_out

    kospi_eval_path = kospi_eval_path or DEFAULT_KOSPI_EVAL
    hero_cal_path = hero_cal_path or DEFAULT_HERO_CAL
    if not kospi_eval_path.is_absolute():
        kospi_eval_path = ROOT / kospi_eval_path
    if not hero_cal_path.is_absolute():
        hero_cal_path = ROOT / hero_cal_path
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    doc = build_shadow_panel(
        kospi_eval=_read_json(kospi_eval_path),
        hero_cal=_read_json(hero_cal_path),
        rules=_read_json(args.rules_json if args.rules_json.is_absolute() else ROOT / args.rules_json),
        as_of_kst=args.as_of_kst,
        year_month=ym,
    )
    doc["inputs"]["kospi_eval_path"] = str(kospi_eval_path).replace("\\", "/")
    doc["inputs"]["hero_calendar_path"] = str(hero_cal_path).replace("\\", "/")

    art_path = args.artifact if args.artifact.is_absolute() else ROOT / args.artifact
    write_paths = [out_path, art_path]
    if out_path != DEFAULT_OUT and DEFAULT_OUT not in write_paths:
        write_paths.append(DEFAULT_OUT)
    if art_path != DEFAULT_ART and DEFAULT_ART not in write_paths:
        write_paths.append(DEFAULT_ART)
    for p in write_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.append_log:
        log_p = args.log_path if args.log_path.is_absolute() else ROOT / args.log_path
        append_log_line(doc, log_p)

    agg = doc.get("aggregate") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "n_scored": agg.get("n_scored"),
                "n_gate_applied": agg.get("n_gate_applied"),
                "active_soft": (agg.get("active") or {}).get("soft_hit_rate"),
                "shadow_soft": (agg.get("shadow") or {}).get("soft_hit_rate"),
                "delta_soft_pp": agg.get("shadow_minus_active_soft_pp"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
