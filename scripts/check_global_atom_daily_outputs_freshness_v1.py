#!/usr/bin/env python3
"""Check freshness of Global Atom daily output artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_report = root / "docs" / "final" / "artifacts" / "global_atom_daily_outputs_freshness_latest.json"
    targets = [
        root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_latest.md",
        root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_public_5line_latest.md",
        root / "docs" / "final" / "artifacts" / "global_atom_corpus_fact_brief_academic_appendix_latest.md",
        root / "docs" / "final" / "artifacts" / "DOMAIN_GRAPH_OPS_DASHBOARD_SUMMARY_LATEST.md",
    ]

    ap = argparse.ArgumentParser(description="Check freshness for daily Global Atom output artifacts.")
    ap.add_argument("--max-age-hours", type=float, default=24.0)
    ap.add_argument("--report-json", default=str(default_report))
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    now = _now()
    rows = []
    failures = []
    for p in targets:
        exists = p.exists()
        age_hours = None
        mtime_utc = None
        fresh = False
        if exists:
            m = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            mtime_utc = _to_iso(m)
            age_hours = (now - m).total_seconds() / 3600.0
            fresh = age_hours <= args.max_age_hours
        else:
            failures.append(f"missing: {p}")

        if exists and not fresh:
            failures.append(f"stale: {p} age_hours={age_hours:.2f}")

        rows.append(
            {
                "path": str(p),
                "exists": exists,
                "mtime_utc": mtime_utc,
                "age_hours": round(age_hours, 4) if isinstance(age_hours, float) else None,
                "fresh": fresh,
            }
        )

    report = {
        "schema": "global_atom_daily_outputs_freshness_v1",
        "checked_at_utc": _to_iso(now),
        "max_age_hours": args.max_age_hours,
        "rows": rows,
        "failures": failures,
        "ok": len(failures) == 0,
    }
    Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
