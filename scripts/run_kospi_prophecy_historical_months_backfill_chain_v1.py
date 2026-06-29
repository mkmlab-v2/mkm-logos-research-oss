#!/usr/bin/env python3
"""Backfill Jan–Apr 2026 KOSPI prophecy calendars + daily eval [HYPO][research_only].

Honest historical OOS extension: builds v2_multilens calendars from session myeongni
panels + scores against kospi_daily_external_yf.csv. Does not inject science_core rows
or fake July scores.

Repro:
  py scripts/run_kospi_prophecy_historical_months_backfill_chain_v1.py
  py scripts/build_kospi_prophecy_only_panel_v1.py
  py scripts/run_kospi_field_band_prophecy_only_chain_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_krx_calendar_v1 import krx_trading_days  # noqa: E402

DEFAULT_MONTHS = ("2026-01", "2026-02", "2026-03", "2026-04")
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_historical_months_backfill_chain_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_prophecy_historical_months_backfill_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_year_month(year_month: str) -> tuple[date, date]:
    parts = str(year_month).strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"year-month must be YYYY-MM, got {year_month!r}")
    y, m = int(parts[0]), int(parts[1])
    start = date(y, m, 1)
    if m == 12:
        end = date(y, 12, 31)
    else:
        end = date(y, m + 1, 1) - timedelta(days=1)
    return start, end


def _last_trading_day(year_month: str) -> str:
    start, end = _parse_year_month(year_month)
    days = krx_trading_days(start, end)
    if not days:
        raise ValueError(f"no KRX trading days for {year_month}")
    return days[-1]


def _paths_for_month(year_month: str) -> tuple[Path, Path]:
    tag = year_month.replace("-", "")
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    return cal, ev


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def run_month(
    year_month: str,
    *,
    profile: str,
    skip_calendar: bool,
    skip_panel_rebuild: bool,
    skip_eval: bool,
) -> dict[str, Any]:
    cal_path, eval_path = _paths_for_month(year_month)
    row: dict[str, Any] = {
        "year_month": year_month,
        "calendar_path": str(cal_path.relative_to(ROOT)).replace("\\", "/"),
        "eval_path": str(eval_path.relative_to(ROOT)).replace("\\", "/"),
        "eval_as_of_kst": _last_trading_day(year_month),
    }

    if not skip_calendar:
        cmd = [
            sys.executable,
            "scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py",
            "--year-month",
            year_month,
            "--profile",
            profile,
        ]
        if skip_panel_rebuild:
            cmd.append("--skip-panel-rebuild")
        rc = _run(cmd)
        row["calendar_exit_code"] = rc
        if rc != 0:
            row["ok"] = False
            return row
        if not cal_path.is_file():
            row["ok"] = False
            row["error"] = "calendar_missing_after_build"
            return row
        cal_doc = json.loads(cal_path.read_text(encoding="utf-8-sig"))
        row["n_trading_days"] = cal_doc.get("n_trading_days")
    else:
        row["calendar_skipped"] = True
        if not cal_path.is_file():
            row["ok"] = False
            row["error"] = "calendar_missing_skip_calendar"
            return row

    if skip_eval:
        row["eval_skipped"] = True
        row["ok"] = True
        return row

    rc = _run(
        [
            sys.executable,
            "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
            "--calendar-json",
            str(cal_path),
            "--as-of-kst",
            row["eval_as_of_kst"],
            "--output",
            str(eval_path),
        ]
    )
    row["eval_exit_code"] = rc
    if rc != 0:
        row["ok"] = False
        return row
    if not eval_path.is_file():
        row["ok"] = False
        row["error"] = "eval_missing_after_run"
        return row
    ev_doc = json.loads(eval_path.read_text(encoding="utf-8-sig"))
    row["n_scored"] = ev_doc.get("n_scored")
    row["band_hit_rate"] = (ev_doc.get("summary") or {}).get("band_hit_rate")
    row["ok"] = True
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--months",
        type=str,
        default=",".join(DEFAULT_MONTHS),
        help="Comma-separated YYYY-MM list (default Jan–Apr 2026)",
    )
    ap.add_argument("--profile", choices=("v1", "v2_multilens"), default="v2_multilens")
    ap.add_argument("--skip-calendar", action="store_true")
    ap.add_argument("--skip-panel-rebuild", action="store_true")
    ap.add_argument("--skip-eval", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    months = [m.strip() for m in str(args.months).split(",") if m.strip()]
    month_rows: list[dict[str, Any]] = []
    ok = True
    for ym in months:
        row = run_month(
            ym,
            profile=args.profile,
            skip_calendar=args.skip_calendar,
            skip_panel_rebuild=args.skip_panel_rebuild,
            skip_eval=args.skip_eval,
        )
        month_rows.append(row)
        if not row.get("ok"):
            ok = False
            break

    doc: dict[str, Any] = {
        "schema": "kospi_prophecy_historical_months_backfill_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_wall": "no_science_core_backfill_no_fake_july",
        "months_requested": months,
        "profile": args.profile,
        "month_results": month_rows,
        "ok": ok,
        "next_steps": [
            "py scripts/build_kospi_prophecy_only_panel_v1.py",
            "py scripts/run_kospi_field_band_prophecy_only_chain_v1.py",
        ],
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "months": len(month_rows), "out": str(args.output)}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
