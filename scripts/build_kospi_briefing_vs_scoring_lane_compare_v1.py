#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build briefing_primary vs scoring_shadow lane HR compare [HYPO][research_only]."""

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

from scripts.kospi_briefing_vs_scoring_lane_lib_v1 import build_lane_compare_report  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
DEFAULT_SCIENCE = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/kospi_briefing_vs_scoring_lane_compare_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_briefing_vs_scoring_lane_compare_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path, Path]:
    tag = year_month.replace("-", "")
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if year_month == "2026-06":
        if not ev.is_file():
            ev = DEFAULT_EVAL
        if not cal.is_file():
            cal = DEFAULT_CAL
    out = ROOT / f"reports/kospi_{tag}_briefing_vs_scoring_lane_compare_v1_latest.json"
    return ev, cal, out, ROOT / f"docs/final/artifacts/kospi_{tag}_briefing_vs_scoring_lane_compare_v1_latest.json"


def build_doc(
    *,
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    science_jsonl: Path,
    year_month: str,
) -> dict[str, Any]:
    doc = build_lane_compare_report(
        eval_doc,
        calendar,
        science_jsonl=science_jsonl,
        year_month=year_month,
    )
    doc["generated_at_utc"] = _utc_now()
    doc["reproduce"] = (
        f"py scripts/build_kospi_briefing_vs_scoring_lane_compare_v1.py --year-month {year_month}"
    )
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--eval-json", type=Path, default=None)
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--artifact", type=Path, default=None)
    ns = ap.parse_args()

    ev_default, cal_default, out_default, art_default = _paths_for_month(ns.year_month)
    eval_path = ns.eval_json or ev_default
    cal_path = ns.calendar_json or cal_default
    out_path = ns.out or out_default
    art_path = ns.artifact or art_default

    eval_doc = _read(eval_path)
    calendar = _read(cal_path)
    doc = build_doc(
        eval_doc=eval_doc,
        calendar=calendar,
        science_jsonl=ns.science_jsonl,
        year_month=ns.year_month,
    )

    for p in (out_path, art_path):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ns.year_month == "2026-06" and out_path != DEFAULT_OUT:
        DEFAULT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        DEFAULT_ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lanes = doc.get("lanes") or {}
    scoring = (lanes.get("scoring_shadow") or {}).get("raw") or {}
    four = (lanes.get("briefing_four_lens_parallel") or {}).get("raw") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "year_month": ns.year_month,
                "out": str(out_path),
                "scoring_soft": scoring.get("soft_hit_rate"),
                "briefing_4l_soft": four.get("soft_hit_rate"),
                "headline_ko": doc.get("headline_ko"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
