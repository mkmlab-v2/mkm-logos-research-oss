#!/usr/bin/env python3
"""Validate Han Vocology KM-VHI pilot observation record (B-track · M8)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "docs/final/artifacts/km_vhi_questionnaire_v0_1_latest.json"
OUT = ROOT / "reports/han_vocology_km_vhi_pilot_validation_v1_latest.json"

ALLOWED_CB = {
    "CB-06-A", "CB-06-B", "CB-08-A", "CB-08-B", "CB-09-A", "CB-09-B",
    "CB-10-A", "CB-10-B", "CB-11", "CB-12", "CB-13", "CB-14", "CB-15", "CB-16",
}
ALLOWED_WEEKS = {0, 4, 8, 12}
FORBIDDEN_PII_KEYS = {"name", "phone", "chart_id", "resident_id", "email", "address"}
CB_EXPECTED_POLICY: dict[str, str] = {
    "CB-06-A": "B1",
    "CB-06-B": "L1",
    "CB-08-A": "A1",
    "CB-08-B": "A1",
    "CB-09-A": "C1",
    "CB-09-B": "C1",
    "CB-10-A": "L1",
    "CB-10-B": "MDT",
    "CB-11": "B1",
    "CB-12": "B1",
    "CB-13": "L1",
    "CB-14": "MDT",
    "CB-15": "MDT",
    "CB-16": "C1",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item_ids(questionnaire: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for sec in questionnaire.get("sections") or []:
        for item in sec.get("items") or []:
            iid = item.get("id")
            if iid:
                ids.append(str(iid))
    return ids


def validate_record(record: dict[str, Any], *, questionnaire: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"name": "schema", "ok": record.get("schema") == "han_vocology_km_vhi_pilot_record_v1"})
    checks.append({"name": "track_b", "ok": record.get("track") == "B"})
    checks.append({"name": "send_gate_hold", "ok": record.get("send_gate") == "HOLD"})

    cb = record.get("cb_id")
    checks.append({"name": "cb_id_allowed", "ok": cb in ALLOWED_CB})

    week = record.get("visit_week")
    checks.append({"name": "visit_week", "ok": week in ALLOWED_WEEKS})

    pii_hits = FORBIDDEN_PII_KEYS.intersection(record.keys())
    checks.append({"name": "no_pii_keys", "ok": not pii_hits, "detail": sorted(pii_hits)})

    checks.append({"name": "pseudonym_present", "ok": bool(str(record.get("pseudonym_id") or "").strip())})
    checks.append({"name": "education_only_ack", "ok": record.get("education_only_ack") is True})
    checks.append(
        {"name": "patient_facing_forbidden_ack", "ok": record.get("patient_facing_forbidden_ack") is True}
    )

    item_ids = _item_ids(questionnaire)
    scores = record.get("scores") or {}
    checks.append({"name": "scores_keys_match", "ok": set(scores.keys()) == set(item_ids)})

    score_ok = all(isinstance(scores.get(k), int) and 0 <= scores[k] <= 4 for k in item_ids)
    checks.append({"name": "scores_range_0_4", "ok": score_ok})

    expected_total = sum(int(scores[k]) for k in item_ids) if score_ok else None
    recorded_total = record.get("total")
    checks.append(
        {
            "name": "total_matches_sum",
            "ok": expected_total is not None and recorded_total == expected_total,
            "expected": expected_total,
            "actual": recorded_total,
        }
    )

    policy = record.get("clinical_policy")
    checks.append({"name": "clinical_policy", "ok": policy in {"B1", "A1", "L1", "C1", "MDT", None}})
    if cb in CB_EXPECTED_POLICY and policy is not None:
        checks.append(
            {
                "name": "policy_matches_cb",
                "ok": policy == CB_EXPECTED_POLICY[cb],
                "expected": CB_EXPECTED_POLICY[cb],
                "actual": policy,
            }
        )

    if week == 0:
        checks.append({"name": "week0_no_delta", "ok": record.get("delta_pct_vs_week0") is None})
    elif week in {4, 8, 12}:
        baseline = record.get("baseline_total_week0")
        delta = record.get("delta_pct_vs_week0")
        if baseline is not None and delta is not None and recorded_total is not None and baseline > 0:
            expected_delta = round((baseline - recorded_total) / baseline * 100, 1)
            checks.append(
                {
                    "name": "delta_pct_consistent",
                    "ok": abs(expected_delta - float(delta)) < 0.15,
                    "expected": expected_delta,
                    "actual": delta,
                }
            )
        else:
            checks.append({"name": "followup_has_baseline_and_delta", "ok": False})

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "cb_id": cb, "visit_week": week}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record-json", type=Path, required=True)
    ap.add_argument("--questionnaire", type=Path, default=QUESTIONNAIRE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    record = json.loads(args.record_json.read_text(encoding="utf-8"))
    questionnaire = json.loads(args.questionnaire.read_text(encoding="utf-8"))
    result = validate_record(record, questionnaire=questionnaire)
    result["generated_at_utc"] = _utc()
    result["record"] = str(args.record_json)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
