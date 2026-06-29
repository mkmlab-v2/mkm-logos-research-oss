#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append manseryeok session myeongni/sasang JSONL through a target date [HYPO].

Merges new KRX weekday rows into existing session JSONL without rewriting full history.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_OUT,
    DEFAULT_SASANG_OUT,
    build_myeongni_session_jsonl_rows,
)

DEFAULT_THROUGH = "2026-06-30"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl_by_day(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ed = str(row.get("eval_date") or row.get("ts_utc") or "")[:10]
        if ed:
            out[ed] = row
    return out


def _write_jsonl(path: Path, rows_by_day: dict[str, dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(rows_by_day[k], ensure_ascii=False) for k in sorted(rows_by_day)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def extend_session_jsonl(
    *,
    through_date: str,
    myeongni_path: Path,
    sasang_path: Path,
    calendar_mode: str = "krx_weekdays",
    neutral_band: float = 0.06,
) -> dict[str, Any]:
    my_by = _load_jsonl_by_day(myeongni_path)
    sa_by = _load_jsonl_by_day(sasang_path)
    prev_max = max(my_by) if my_by else None
    if not prev_max:
        date_from = "1996-12-11"
    else:
        date_from = (date.fromisoformat(prev_max) + timedelta(days=1)).isoformat()

    if date.fromisoformat(date_from) > date.fromisoformat(through_date):
        return {
            "ok": True,
            "already_through": through_date,
            "prev_max": prev_max,
            "n_appended": 0,
        }

    my_new, sa_new, panel_meta = build_myeongni_session_jsonl_rows(
        date_from=date_from,
        date_to=through_date,
        calendar_mode=calendar_mode,
        neutral_band=neutral_band,
    )
    n_my_before = len(my_by)
    n_sa_before = len(sa_by)
    for row in my_new:
        my_by[str(row["eval_date"])[:10]] = row
    for row in sa_new:
        sa_by[str(row["eval_date"])[:10]] = row

    n_my = _write_jsonl(myeongni_path, my_by)
    n_sa = _write_jsonl(sasang_path, sa_by)
    new_max = max(my_by) if my_by else None

    return {
        "ok": True,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "through_date": through_date,
        "date_from_new": date_from,
        "prev_max": prev_max,
        "new_max": new_max,
        "n_appended_myeongni": len(my_new),
        "n_appended_sasang": len(sa_new),
        "n_total_myeongni": n_my,
        "n_total_sasang": n_sa,
        "delta_myeongni": n_my - n_my_before,
        "delta_sasang": n_sa - n_sa_before,
        "panel_meta": panel_meta,
        "paths": {
            "myeongni": str(myeongni_path).replace("\\", "/"),
            "sasang": str(sasang_path).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--through-date", default=DEFAULT_THROUGH)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_OUT)
    ap.add_argument("--calendar-mode", default="krx_weekdays", choices=("all", "krx_weekdays"))
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--report", type=Path, default=ROOT / "reports/extend_manseryeok_session_jsonl_v1_latest.json")
    args = ap.parse_args()

    doc = extend_session_jsonl(
        through_date=args.through_date.strip()[:10],
        myeongni_path=args.myeongni_jsonl if args.myeongni_jsonl.is_absolute() else ROOT / args.myeongni_jsonl,
        sasang_path=args.sasang_jsonl if args.sasang_jsonl.is_absolute() else ROOT / args.sasang_jsonl,
        calendar_mode=args.calendar_mode,
        neutral_band=args.neutral_band,
    )
    rep = args.report if args.report.is_absolute() else ROOT / args.report
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
