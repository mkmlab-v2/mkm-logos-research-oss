#!/usr/bin/env python3
"""NEWS-HP-RT refresh gate — cohort/market freeze until not_before [HYPO / research_only]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_hp_rt_refresh_gate_v1_latest.json"
HP_BENCH = ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json"
COHORT = ART / "news_observation_v1_latest.jsonl"
DEFAULT_NOT_BEFORE = "2026-06-08"
DEFAULT_MIN_HOURS = 144


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _hours_since(ts: str | None) -> float | None:
    dt = _parse_utc(ts)
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def _mtime_utc(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate_gate(
    *,
    not_before: str = DEFAULT_NOT_BEFORE,
    min_hours_since_bench: float = DEFAULT_MIN_HOURS,
    force: bool = False,
) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    calendar_open = today >= not_before
    bench = {}
    if HP_BENCH.is_file():
        bench = json.loads(HP_BENCH.read_text(encoding="utf-8"))
    last_bench_utc = bench.get("generated_at_utc")
    hours_since = _hours_since(last_bench_utc)
    cohort_mtime = _mtime_utc(COHORT)
    bench_mtime = _mtime_utc(HP_BENCH)
    cohort_newer = False
    if cohort_mtime and bench_mtime:
        cohort_newer = cohort_mtime > bench_mtime
    interval_ok = hours_since is None or hours_since >= min_hours_since_bench
    refresh_recommended = calendar_open and (interval_ok or cohort_newer)
    refresh_allowed = force or refresh_recommended

    reasons: list[str] = []
    if not calendar_open and not force:
        reasons.append(f"calendar_gate:not_before={not_before}")
    if calendar_open and not interval_ok and not cohort_newer and not force:
        reasons.append(f"interval_gate:min_hours={min_hours_since_bench}")
    if force:
        reasons.append("force_override")

    return {
        "schema": "saving_the_news_news_hp_rt_refresh_gate_v1",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "generated_at_utc": _utc_now(),
        "not_before_date": not_before,
        "today_utc": today,
        "calendar_gate_open": calendar_open,
        "min_hours_since_bench": min_hours_since_bench,
        "hours_since_last_bench": hours_since,
        "cohort_path": "docs/final/artifacts/news_observation_v1_latest.jsonl",
        "cohort_mtime_utc": cohort_mtime,
        "last_bench_generated_at_utc": last_bench_utc,
        "cohort_newer_than_bench": cohort_newer,
        "refresh_recommended": refresh_recommended,
        "refresh_allowed": refresh_allowed,
        "decision_label": "GO_REFRESH" if refresh_allowed else "HOLD_WATCH",
        "cms_publish_allowed": False,
        "blocked_reasons": reasons if not refresh_allowed else [],
        "explicit_next": [
            "Full NEWS-HP-RT re-bench via Invoke-SavingTheNewsNewsHpRtRefresh_v1.ps1",
            "Daily pre-news uses intake-only (-SkipHpBench); weekly task runs full bench",
            "Delta is research_only — not Track A promotion",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--not-before", default=DEFAULT_NOT_BEFORE)
    ap.add_argument("--min-hours-since-bench", type=float, default=DEFAULT_MIN_HOURS)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--write-json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when refresh not allowed.")
    args = ap.parse_args()

    doc = evaluate_gate(
        not_before=args.not_before,
        min_hours_since_bench=args.min_hours_since_bench,
        force=args.force,
    )
    if args.write_json:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_JSON}")

    print(
        f"gate decision={doc['decision_label']} "
        f"calendar_open={doc['calendar_gate_open']} refresh_allowed={doc['refresh_allowed']}"
    )
    if args.strict and not doc["refresh_allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
