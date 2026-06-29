#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build June KOSPI calendar-eval miss decomposition for flow probe [HYPO][research_only]."""

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

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_calendar_miss_decomposition_v1_latest.json"
SCHEMA = "kospi_june2026_calendar_miss_decomposition_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _tags(pred: str, actual: str, band_hit: bool | None) -> list[str]:
    out = [f"{pred}_pred_{actual}_actual"]
    if band_hit is True:
        out.append("band_hit_despite_direction_miss")
    elif band_hit is False:
        out.append("band_miss")
    return out


def build_miss_decomposition(eval_doc: dict[str, Any], *, eval_path: Path) -> dict[str, Any]:
    rows = [r for r in (eval_doc.get("rows") or []) if isinstance(r, dict)]
    miss_days: list[dict[str, Any]] = []
    for r in rows:
        if str(r.get("outcome") or "") != "FAIL":
            continue
        pred = str(r.get("predicted_direction") or "")
        actual = str(r.get("actual_direction") or "")
        miss_days.append(
            {
                "eval_date": str(r.get("session_date") or "")[:10],
                "kospi_pred": pred,
                "kospi_actual": actual,
                "kospi_ret_pct": r.get("daily_return_pct"),
                "prior_close": r.get("prior_close"),
                "actual_close": r.get("actual_close"),
                "predicted_close_mid": r.get("predicted_close_mid"),
                "band_hit": r.get("band_hit"),
                "tags": _tags(pred, actual, r.get("band_hit")),
            }
        )

    return {
        "schema": SCHEMA,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "source": "kospi_june2026_daily_prophecy_eval",
        "eval_path": str(eval_path.relative_to(ROOT)).replace("\\", "/"),
        "as_of_kst": eval_doc.get("as_of_kst"),
        "year_month": eval_doc.get("year_month"),
        "n_scored": eval_doc.get("n_scored"),
        "miss_day_count": len(miss_days),
        "miss_days": miss_days,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    eval_path = args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json
    if not eval_path.is_file():
        print(f"missing eval: {eval_path}", file=sys.stderr)
        return 2

    doc = build_miss_decomposition(_load(eval_path), eval_path=eval_path)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} miss_days={doc['miss_day_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
