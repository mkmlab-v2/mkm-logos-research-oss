#!/usr/bin/env python3
"""Discover scored prophecy-only month eval/calendar pairs (no backfill) [HYPO]."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PROPHECY_MONTH_SOURCES: list[tuple[str, Path, Path]] = [
    (
        "202601",
        ROOT / "reports/kospi_202601_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202601_daily_prophecy_calendar_v1.json",
    ),
    (
        "202602",
        ROOT / "reports/kospi_202602_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202602_daily_prophecy_calendar_v1.json",
    ),
    (
        "202603",
        ROOT / "reports/kospi_202603_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202603_daily_prophecy_calendar_v1.json",
    ),
    (
        "202604",
        ROOT / "reports/kospi_202604_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202604_daily_prophecy_calendar_v1.json",
    ),
    (
        "202605",
        ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json",
    ),
    (
        "202606",
        ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
    ),
    (
        "202607",
        ROOT / "reports/kospi_202607_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_202607_daily_prophecy_calendar_v1.json",
    ),
]

_VALID_DIRECTIONS = frozenset({"bull", "bear", "neutral"})


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _scored_prophecy_rows(eval_doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in eval_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if row.get("backfill_source"):
            continue
        if row.get("actual_direction") not in _VALID_DIRECTIONS:
            continue
        out.append(row)
    return out


def discover_prophecy_only_inputs(
    sources: list[tuple[str, Path, Path]] | None = None,
) -> tuple[list[Path], list[Path], list[str]]:
    """Return eval paths, calendar paths, and included year_month keys."""
    eval_paths: list[Path] = []
    calendar_paths: list[Path] = []
    months: list[str] = []
    for ym, eval_path, cal_path in sources or PROPHECY_MONTH_SOURCES:
        ev = _read(eval_path)
        if not ev or not cal_path.is_file():
            continue
        if not _scored_prophecy_rows(ev):
            continue
        eval_paths.append(eval_path)
        calendar_paths.append(cal_path)
        months.append(ym)
    return eval_paths, calendar_paths, months


def prophecy_only_panel_label(months: list[str]) -> str:
    if not months:
        return "prophecy_only_empty"
    if months == ["202605", "202606"]:
        return "prophecy_only_may_june"
    if months == ["202601", "202602", "202603", "202604", "202605", "202606"]:
        return "prophecy_only_jan_jun_2026"
    return "prophecy_only_" + "_".join(m.replace("2026", "") for m in months)
