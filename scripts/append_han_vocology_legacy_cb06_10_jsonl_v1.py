#!/usr/bin/env python3
"""Append CB-06~10 legacy cohort rows to pilot JSONL (B-track · M15 · idempotent)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"

LEGACY_CB = {
    "CB-06-A", "CB-06-B", "CB-08-A", "CB-08-B", "CB-09-A", "CB-09-B", "CB-10-A", "CB-10-B",
}

# (pseudonym, site, cb_id, policy, visits[(week, total, scores), ...])
LEGACY: list[tuple[str, str, str, str, list[tuple[int, int, dict[str, int]]]]] = [
    ("PILOT-06A-001", "SITE-LEG-01", "CB-06-A", "B1", [
        (0, 38, {"F1": 4, "F2": 4, "F3": 4, "E1": 4, "E2": 4, "E3": 3, "P1": 4, "P2": 4, "P3": 4, "P4": 3}),
        (4, 24, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
        (8, 20, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 3}),
    ]),
    ("PILOT-06B-001", "SITE-LEG-02", "CB-06-B", "L1", [
        (0, 32, {"F1": 3, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 3, "P1": 4, "P2": 4, "P3": 3, "P4": 3}),
        (4, 24, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
        (8, 22, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 2, "P2": 2, "P3": 3, "P4": 3}),
    ]),
    ("PILOT-08A-001", "SITE-LEG-03", "CB-08-A", "A1", [
        (0, 34, {"F1": 4, "F2": 4, "F3": 3, "E1": 4, "E2": 3, "E3": 3, "P1": 4, "P2": 4, "P3": 3, "P4": 2}),
        (4, 26, {"F1": 2, "F2": 3, "F3": 2, "E1": 3, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
        (8, 22, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 3, "P2": 2, "P3": 3, "P4": 2}),
    ]),
    ("PILOT-08B-001", "SITE-LEG-04", "CB-08-B", "A1", [
        (0, 28, {"F1": 3, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 2}),
        (4, 22, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 2, "P2": 2, "P3": 3, "P4": 3}),
        (8, 20, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 3}),
    ]),
    ("PILOT-09A-001", "SITE-LEG-05", "CB-09-A", "C1", [
        (0, 38, {"F1": 4, "F2": 4, "F3": 4, "E1": 4, "E2": 4, "E3": 3, "P1": 4, "P2": 4, "P3": 4, "P4": 3}),
        (4, 30, {"F1": 3, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 4}),
        (8, 28, {"F1": 4, "F2": 3, "F3": 2, "E1": 3, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
    ]),
    ("PILOT-09B-001", "SITE-LEG-06", "CB-09-B", "C1", [
        (0, 40, {"F1": 4, "F2": 4, "F3": 4, "E1": 4, "E2": 4, "E3": 4, "P1": 4, "P2": 4, "P3": 4, "P4": 4}),
        (4, 28, {"F1": 3, "F2": 3, "F3": 3, "E1": 3, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
        (8, 26, {"F1": 2, "F2": 3, "F3": 2, "E1": 3, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
    ]),
    ("PILOT-10A-001", "SITE-LEG-07", "CB-10-A", "L1", [
        (0, 36, {"F1": 4, "F2": 4, "F3": 4, "E1": 4, "E2": 3, "E3": 3, "P1": 4, "P2": 4, "P3": 3, "P4": 3}),
        (4, 24, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 3}),
        (8, 22, {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 2, "P2": 2, "P3": 3, "P4": 3}),
    ]),
    ("PILOT-10B-001", "SITE-LEG-08", "CB-10-B", "MDT", [
        (0, 38, {"F1": 4, "F2": 4, "F3": 4, "E1": 4, "E2": 4, "E3": 3, "P1": 4, "P2": 4, "P3": 4, "P4": 3}),
        (4, 32, {"F1": 4, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 3, "P1": 3, "P2": 3, "P3": 3, "P4": 4}),
        (8, 30, {"F1": 3, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 2, "P1": 3, "P2": 3, "P3": 3, "P4": 4}),
        (12, 28, {"F1": 4, "F2": 3, "F3": 3, "E1": 3, "E2": 3, "E3": 2, "P1": 3, "P2": 3, "P3": 2, "P4": 2}),
    ]),
]

WEEK_DATES = {
    0: "2026-03-10T09:00:00+00:00",
    4: "2026-04-07T09:00:00+00:00",
    8: "2026-05-05T09:00:00+00:00",
    12: "2026-06-02T09:00:00+00:00",
}


def _delta(baseline: int, total: int) -> float:
    return round((baseline - total) / baseline * 100, 1)


def _record(
    *,
    pseudonym: str,
    site: str,
    cb_id: str,
    policy: str,
    week: int,
    scores: dict[str, int],
    total: int,
    baseline: int | None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "schema": "han_vocology_km_vhi_pilot_record_v1",
        "version": "0.1.0",
        "track": "B",
        "send_gate": "HOLD",
        "site_id": site,
        "pseudonym_id": pseudonym,
        "cb_id": cb_id,
        "visit_week": week,
        "collected_at_utc": WEEK_DATES[week],
        "scores": scores,
        "total": total,
        "clinical_policy": policy,
        "education_only_ack": True,
        "patient_facing_forbidden_ack": True,
    }
    if week != 0 and baseline is not None:
        rec["baseline_total_week0"] = baseline
        rec["delta_pct_vs_week0"] = _delta(baseline, total)
    return rec


def _verify_totals() -> None:
    for _pid, _site, _cb, _pol, visits in LEGACY:
        for week, total, scores in visits:
            s = sum(scores.values())
            if s != total:
                raise SystemExit(f"sum mismatch { _cb } w{week}: {s} != {total}")


def main() -> int:
    _verify_totals()

    existing: list[dict[str, Any]] = []
    if JSONL.is_file():
        for line in JSONL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))

    present_cb = {str(r.get("cb_id")) for r in existing}
    if LEGACY_CB.issubset(present_cb):
        print(json.dumps({"ok": True, "skipped": True, "reason": "legacy_already_present", "rows": len(existing)}))
        return 0

    baseline_by_patient: dict[str, int] = {}
    new_rows: list[dict[str, Any]] = []
    for pseudonym, site, cb_id, policy, visits in LEGACY:
        w0_total = next(t for w, t, _ in visits if w == 0)
        baseline_by_patient[pseudonym] = w0_total
        for week, total, scores in visits:
            new_rows.append(
                _record(
                    pseudonym=pseudonym,
                    site=site,
                    cb_id=cb_id,
                    policy=policy,
                    week=week,
                    scores=scores,
                    total=total,
                    baseline=None if week == 0 else w0_total,
                )
            )

    merged = existing + new_rows
    JSONL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "appended": len(new_rows), "total_rows": len(merged), "legacy_cohorts": 8},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
