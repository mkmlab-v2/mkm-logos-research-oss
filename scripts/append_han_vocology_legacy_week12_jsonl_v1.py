#!/usr/bin/env python3
"""Append legacy 12-week cohort week-12 rows to pilot JSONL (B-track · M18 · idempotent)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"

# case bank §470–477 · §8.3 (CB-08-A w12=20) · 12주 SOAP §811
WEEK12: list[tuple[str, str, str, str, int, dict[str, int], str]] = [
    (
        "PILOT-06A-001",
        "SITE-LEG-01",
        "CB-06-A",
        "B1",
        20,
        {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 3},
        "2026-06-09T09:00:00+00:00",
    ),
    (
        "PILOT-06B-001",
        "SITE-LEG-02",
        "CB-06-B",
        "L1",
        20,
        {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 3},
        "2026-06-16T09:00:00+00:00",
    ),
    (
        "PILOT-08A-001",
        "SITE-LEG-03",
        "CB-08-A",
        "A1",
        20,
        {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 2, "P1": 2, "P2": 2, "P3": 2, "P4": 2},
        "2026-06-23T09:00:00+00:00",
    ),
    (
        "PILOT-10A-001",
        "SITE-LEG-07",
        "CB-10-A",
        "L1",
        20,
        {"F1": 2, "F2": 2, "F3": 2, "E1": 2, "E2": 2, "E3": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 3},
        "2026-06-30T09:00:00+00:00",
    ),
]


def _delta(baseline: int, total: int) -> float:
    return round((baseline - total) / baseline * 100, 1)


def _record(
    *,
    pseudonym: str,
    site: str,
    cb_id: str,
    policy: str,
    total: int,
    scores: dict[str, int],
    collected_at: str,
    baseline: int,
) -> dict[str, Any]:
    return {
        "schema": "han_vocology_km_vhi_pilot_record_v1",
        "version": "0.1.0",
        "track": "B",
        "send_gate": "HOLD",
        "site_id": site,
        "pseudonym_id": pseudonym,
        "cb_id": cb_id,
        "visit_week": 12,
        "collected_at_utc": collected_at,
        "scores": scores,
        "total": total,
        "baseline_total_week0": baseline,
        "delta_pct_vs_week0": _delta(baseline, total),
        "clinical_policy": policy,
        "education_only_ack": True,
        "patient_facing_forbidden_ack": True,
    }


def main() -> int:
    for _pid, _site, _cb, _pol, total, scores, _at in WEEK12:
        if sum(scores.values()) != total:
            raise SystemExit(f"sum mismatch {_cb} w12: {sum(scores.values())} != {total}")

    existing: list[dict[str, Any]] = []
    if JSONL.is_file():
        for line in JSONL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))

    have_w12 = {
        (str(r.get("pseudonym_id")), int(r.get("visit_week") or -1))
        for r in existing
        if r.get("visit_week") == 12
    }
    targets = {(pid, 12) for pid, *_ in WEEK12}
    if targets.issubset(have_w12):
        print(json.dumps({"ok": True, "skipped": True, "reason": "week12_already_present", "rows": len(existing)}))
        return 0

    baseline_by_patient: dict[str, int] = {}
    for r in existing:
        if r.get("visit_week") == 0:
            baseline_by_patient[str(r.get("pseudonym_id"))] = int(r.get("total") or 0)

    new_rows: list[dict[str, Any]] = []
    for pseudonym, site, cb_id, policy, total, scores, collected_at in WEEK12:
        if (pseudonym, 12) in have_w12:
            continue
        baseline = baseline_by_patient.get(pseudonym)
        if baseline is None:
            raise SystemExit(f"missing week0 baseline for {pseudonym}")
        new_rows.append(
            _record(
                pseudonym=pseudonym,
                site=site,
                cb_id=cb_id,
                policy=policy,
                total=total,
                scores=scores,
                collected_at=collected_at,
                baseline=baseline,
            )
        )

    merged = existing + new_rows
    JSONL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "appended": len(new_rows), "total_rows": len(merged), "week12_legacy": len(new_rows)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
