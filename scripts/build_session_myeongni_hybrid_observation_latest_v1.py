#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh session-myeongni hybrid observation JSON (B-track, non-fatal for daily chain)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/session_myeongni_hybrid_observation_latest.json"
HOLDOUT_SUMMARY = ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, cwd=str(ROOT))
    return int(r.returncode)


def _read_eval(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _hit(doc: dict[str, Any] | None) -> float | None:
    if not doc:
        return None
    m = doc.get("metrics") or {}
    return m.get("price_directional_hit_rate")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-days", type=int, default=30, help="Rolling eval window for daily observation.")
    ap.add_argument("--panel-calendar-days", type=int, default=50, help="Calendar span for session panel build.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-holdout-summary", action="store_true")
    args = ap.parse_args()

    today = date.today()
    panel_from = (today - timedelta(days=max(args.panel_calendar_days, args.eval_days + 10))).isoformat()
    panel_to = today.isoformat()
    tag = f"obs_{args.eval_days}d"

    panel_csv = ROOT / "reports" / f"btrack_session_myeongni_panel_{tag}.csv"
    per_date = ROOT / "reports" / f"btrack_per_date_directions_session_myeongni_{tag}.json"
    hybrid_score = ROOT / "reports" / f"btrack_prophecy_score_hybrid_session_kospi_{tag}.json"
    eval_kospi = ROOT / "reports" / f"prophecy_hit_rate_hybrid_obs_{tag}_kospi.json"
    eval_btc = ROOT / "reports" / f"prophecy_hit_rate_hybrid_obs_{tag}_btc.json"

    steps: list[dict[str, Any]] = []

    def step(name: str, cmd: list[str]) -> bool:
        rc = _run(cmd)
        steps.append({"step": name, "exit_code": rc})
        return rc == 0

    ok = step(
        "panel",
        [
            sys.executable,
            "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
            "--date-from",
            panel_from,
            "--date-to",
            panel_to,
            "--out-csv",
            str(panel_csv),
        ],
    )
    if not ok:
        print("panel failed", file=sys.stderr)
        return 2

    ok = step(
        "per_date",
        [
            sys.executable,
            "scripts/build_myeongni_jsonl_from_manseryeok_session_v1.py",
            "--date-from",
            panel_from,
            "--date-to",
            panel_to,
            f"--myeongni-out=data/myeongni/myeongni_session_{tag}.jsonl",
        ],
    )
    if not ok:
        print("session jsonl failed", file=sys.stderr)
        return 2

    ok = step(
        "per_date_export",
        [
            sys.executable,
            "scripts/build_btrack_per_date_directions_from_session_jsonl_v1.py",
            "--session-jsonl",
            f"data/myeongni/myeongni_session_{tag}.jsonl",
            "--out",
            str(per_date),
        ],
    )
    if not ok:
        return 2

    ok = step(
        "hybrid_score",
        [
            sys.executable,
            "scripts/build_btrack_prophecy_score_hybrid_session_kospi_v1.py",
            "--session-per-date-json",
            str(per_date),
            "--recent-trading-days",
            str(args.eval_days),
            "--output",
            str(hybrid_score),
        ],
    )
    if not ok:
        return 2

    step(
        "eval_kospi",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(hybrid_score),
            "--headline-instrument",
            "kospi",
            "--output",
            str(eval_kospi),
        ],
    )
    step(
        "eval_btc",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(hybrid_score),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_btc),
        ],
    )

    # Today session pillars from panel tail
    today_pillars: dict[str, str] | None = None
    today_score: float | None = None
    today_map: str | None = None
    if panel_csv.is_file():
        import csv

        rows = list(csv.DictReader(panel_csv.open(encoding="utf-8-sig")))
        for r in reversed(rows):
            if str(r.get("session_local_date", ""))[:10] == panel_to:
                today_pillars = {
                    "year": r.get("year_pillar", ""),
                    "month": r.get("month_pillar", ""),
                    "day": r.get("day_pillar", ""),
                    "hour": r.get("hour_pillar", ""),
                }
                break
    if per_date.is_file():
        doc = json.loads(per_date.read_text(encoding="utf-8"))
        for row in reversed(doc.get("rows") or []):
            if str(row.get("eval_date", ""))[:10] == panel_to:
                today_map = str(row.get("mapping_target") or "")
                sc = row.get("session_direction_score")
                today_score = float(sc) if sc is not None else None
                break

    holdout_block: dict[str, Any] | None = None
    if not args.skip_holdout_summary and HOLDOUT_SUMMARY.is_file():
        holdout_block = json.loads(HOLDOUT_SUMMARY.read_text(encoding="utf-8"))

    out_doc = {
        "schema": "session_myeongni_hybrid_observation_latest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autotrigger_forbidden": True,
        "hybrid_rule": "kospi=session_per_date; btc=frozen_bear",
        "rolling_eval": {
            "eval_days": args.eval_days,
            "kospi_hit_rate": _hit(_read_eval(eval_kospi)),
            "btc_hit_rate": _hit(_read_eval(eval_btc)),
            "score_json": str(hybrid_score.relative_to(ROOT)).replace("\\", "/"),
        },
        "holdout_252d": holdout_block,
        "today": {
            "session_local_date": panel_to,
            "pillars_session": today_pillars,
            "session_direction_score": today_score,
            "mapping_target": today_map,
            "kospi_predicted": "neutral" if today_map == "sideways" else today_map,
            "btc_predicted": "bear",
        },
        "pipeline_steps": steps,
        "note_ko": "관측 전용. Track A·실매매·btrack_prophecy_score_latest 덮어쓰기 없음.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
