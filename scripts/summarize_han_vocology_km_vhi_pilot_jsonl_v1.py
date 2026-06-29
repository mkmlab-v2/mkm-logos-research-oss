#!/usr/bin/env python3
"""Summarize Han Vocology KM-VHI pilot JSONL cohorts (B-track · M9)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
OUT = ROOT / "reports/han_vocology_km_vhi_pilot_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarize(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    cohorts: dict[str, dict[str, Any]] = {}
    for r in rows:
        pid = str(r.get("pseudonym_id") or "")
        entry = cohorts.setdefault(
            pid,
            {
                "pseudonym_id": pid,
                "site_id": r.get("site_id"),
                "cb_id": r.get("cb_id"),
                "clinical_policy": r.get("clinical_policy"),
                "visits": {},
            },
        )
        week_raw = r.get("visit_week")
        week = int(week_raw) if week_raw is not None else -1
        entry["visits"][str(week)] = {
            "total": r.get("total"),
            "delta_pct_vs_week0": r.get("delta_pct_vs_week0"),
        }

    site_patients: dict[str, set[str]] = {}
    for r in rows:
        sid = str(r.get("site_id") or "")
        site_patients.setdefault(sid, set()).add(str(r.get("pseudonym_id")))
    sites_summary = {k: {"patients": sorted(v), "patient_count": len(v)} for k, v in site_patients.items()}

    return {
        "schema": "han_vocology_km_vhi_pilot_summary_v1",
        "row_count": len(rows),
        "cohort_count": len(cohorts),
        "cohorts": list(cohorts.values()),
        "sites": sites_summary,
        "send_gate": "HOLD",
        "track": "B",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "jsonl_missing"}, ensure_ascii=False))
        return 1

    data = summarize(args.jsonl)
    data["generated_at_utc"] = _utc()
    data["jsonl"] = str(args.jsonl)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "cohort_count": data["cohort_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
