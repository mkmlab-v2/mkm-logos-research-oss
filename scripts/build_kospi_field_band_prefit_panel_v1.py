#!/usr/bin/env python3
"""Build KOSPI science_core prefit panel (pre-May, no prophecy overlap) [HYPO]."""
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

from scripts.build_kospi_multi_month_prophecy_panel_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL,
    build_science_core_backfill,
)

DEFAULT_EVAL_OUT = ROOT / "reports/kospi_field_band_prefit_panel_eval_v1_latest.json"
DEFAULT_CAL_OUT = ROOT / "reports/kospi_field_band_prefit_panel_calendar_v1_latest.json"
ART_EVAL = ROOT / "docs/final/artifacts/kospi_field_band_prefit_panel_eval_v1_latest.json"
ART_CAL = ROOT / "docs/final/artifacts/kospi_field_band_prefit_panel_calendar_v1_latest.json"
PREFIT_CUTOFF = "2026-05-01"
# Jan–Apr prophecy backfill shares calendar dates with science_core; prefit train
# still uses science_core pre-May. Only exclude May+ prophecy dates from science rows.
PREFIT_PROPHECY_OVERLAP_EXCLUDE_FROM = "2026-05-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prophecy_dates() -> set[str]:
    path = ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json"
    if not path.is_file():
        return set()
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return set()
    return {
        str(r.get("session_date"))
        for r in (doc.get("rows") or [])
        if isinstance(r, dict)
        and r.get("session_date")
        and str(r.get("session_date")) >= PREFIT_PROPHECY_OVERLAP_EXCLUDE_FROM
    }


def build_prefit_panel(
    *,
    science_jsonl: Path,
    date_from: str = "2026-01-02",
    date_to: str = "2026-04-30",
) -> tuple[dict[str, Any], dict[str, Any]]:
    exclude = _prophecy_dates()
    eval_rows, cal_rows = build_science_core_backfill(
        jsonl_path=science_jsonl,
        exclude_dates=exclude,
        date_from=date_from,
        date_to=date_to,
    )
    eval_rows = [r for r in eval_rows if str(r.get("session_date") or "") < PREFIT_CUTOFF]
    cal_rows = [r for r in cal_rows if str(r.get("session_date") or "") < PREFIT_CUTOFF]
    trading_days = sorted({str(r.get("session_date")) for r in eval_rows if r.get("session_date")})
    ev = {
        "schema": "kospi_field_band_prefit_panel_eval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "panel_label": "prefit_science_core_kospi_pre_may",
        "train_source": "science_core_uniform_band",
        "prefit_cutoff_exclusive": PREFIT_CUTOFF,
        "n_scored": len(eval_rows),
        "rows": eval_rows,
    }
    cal = {
        "schema": "kospi_field_band_prefit_panel_calendar_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "panel_label": "prefit_science_core_kospi_pre_may",
        "train_source": "science_core_uniform_band",
        "prefit_cutoff_exclusive": PREFIT_CUTOFF,
        "n_trading_days": len(trading_days),
        "trading_days": trading_days,
        "rows": cal_rows,
    }
    return ev, cal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--calendar-out", type=Path, default=DEFAULT_CAL_OUT)
    args = ap.parse_args()

    if not args.science_jsonl.is_file():
        print(json.dumps({"ok": False, "error": "science_jsonl_missing"}, ensure_ascii=False), file=sys.stderr)
        return 2

    ev, cal = build_prefit_panel(science_jsonl=args.science_jsonl)
    if int(ev.get("n_scored") or 0) < 20:
        print(json.dumps({"ok": False, "error": "prefit_n_too_small", "n": ev.get("n_scored")}, ensure_ascii=False), file=sys.stderr)
        return 2

    for path, doc, art in (
        (args.eval_out, ev, ART_EVAL),
        (args.calendar_out, cal, ART_CAL),
    ):
        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text(payload, encoding="utf-8")

    print(json.dumps({"ok": True, "n_scored": ev["n_scored"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
