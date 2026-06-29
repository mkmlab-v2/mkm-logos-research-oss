#!/usr/bin/env python3
"""Build multi-month prophecy-only panel (no science_core backfill) [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_multi_month_prophecy_panel_v1 import build_multi_month_panel  # noqa: E402
from scripts.kospi_prophecy_only_panel_inputs_v1 import (  # noqa: E402
    discover_prophecy_only_inputs,
    prophecy_only_panel_label,
)

DEFAULT_EVAL_OUT = ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json"
DEFAULT_CAL_OUT = ROOT / "reports/kospi_prophecy_only_panel_calendar_v1_latest.json"
ART_EVAL = ROOT / "docs/final/artifacts/kospi_prophecy_only_panel_eval_v1_latest.json"
ART_CAL = ROOT / "docs/final/artifacts/kospi_prophecy_only_panel_calendar_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--calendar-out", type=Path, default=DEFAULT_CAL_OUT)
    args = ap.parse_args()

    eval_paths, calendar_paths, months = discover_prophecy_only_inputs()
    if not eval_paths:
        print(json.dumps({"ok": False, "error": "no_scored_prophecy_months"}, ensure_ascii=False), file=sys.stderr)
        return 2

    ev, cal = build_multi_month_panel(
        eval_paths=eval_paths,
        calendar_paths=calendar_paths,
        include_science_backfill=False,
        panel_label=prophecy_only_panel_label(months),
    )
    ev["included_prophecy_months"] = months
    cal["included_prophecy_months"] = months
    for path, doc, art in (
        (args.eval_out, ev, ART_EVAL),
        (args.calendar_out, cal, ART_CAL),
    ):
        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": ev["n_scored"],
                "n_months": ev.get("n_months"),
                "included_prophecy_months": months,
                "science_backfill_rows": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
