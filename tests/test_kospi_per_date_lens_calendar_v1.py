"""Per-date lens mode on KOSPI calendar builder (shadow)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar


def test_build_calendar_per_date_mode_differs_from_static():
    static_doc = build_calendar(year_month="2026-06", skip_panel=True, lens_mode="static")
    per_date_doc = build_calendar(year_month="2026-06", skip_panel=True, lens_mode="per_date")
    assert per_date_doc.get("lens_mode") == "per_date"
    assert per_date_doc.get("shadow_calendar") is True
    assert per_date_doc.get("published_calendar_forbidden") is True
    static_dirs = {r["session_date"]: r["predicted_direction"] for r in static_doc["rows"]}
    per_dirs = {r["session_date"]: r["predicted_direction"] for r in per_date_doc["rows"]}
    diffs = [d for d in static_dirs if static_dirs.get(d) != per_dirs.get(d)]
    assert len(diffs) >= 1, "expected at least one direction diff static vs per_date"


def test_per_date_shadow_path_helper():
    from scripts.kospi_lens_per_date_static_v1 import per_date_shadow_calendar_path

    p = per_date_shadow_calendar_path("2026-07")
    assert p.name == "kospi_202607_per_date_lens_shadow_calendar_v1.json"
