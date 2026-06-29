#!/usr/bin/env python3
"""Compute digestion pass-rate metrics for DR bench promotion columns (B-track)."""

from __future__ import annotations

from typing import Any

from scripts.check_mkm_digested_facts_gate_v1 import run_gate


def compute_digested_digest_metrics(digested_doc: dict[str, Any]) -> dict[str, Any]:
    facts = digested_doc.get("facts") or []
    fact_count = len(facts)
    wired_count = sum(1 for e in (digested_doc.get("wiring_manifest") or []) if e.get("wired"))
    if wired_count == 0:
        wired_count = sum(1 for f in facts if (f.get("mkm_wiring") or {}).get("wired"))

    status_counts = {"Right": 0, "Wrong": 0, "Unknown": 0}
    for fact in facts:
        status = str((fact.get("verification") or {}).get("status") or "Unknown")
        if status not in status_counts:
            status = "Unknown"
        status_counts[status] += 1

    gate_doc = run_gate(digested_doc)
    gate_entries = gate_doc.get("entries") or []
    gate_pass = sum(1 for e in gate_entries if e.get("gate_status") == "pass")
    gate_fail = sum(1 for e in gate_entries if e.get("gate_status") == "fail")
    gate_skipped = sum(1 for e in gate_entries if e.get("gate_status") == "skipped")
    gate_eligible = gate_pass + gate_fail

    wiring_rate = round(wired_count / fact_count, 4) if fact_count else 0.0
    verification_right_rate = round(status_counts["Right"] / fact_count, 4) if fact_count else 0.0
    gate_pass_rate = round(gate_pass / gate_eligible, 4) if gate_eligible else 0.0

    return {
        "fact_count": fact_count,
        "wired_count": wired_count,
        "wiring_rate": wiring_rate,
        "verification_right_count": status_counts["Right"],
        "verification_wrong_count": status_counts["Wrong"],
        "verification_unknown_count": status_counts["Unknown"],
        "verification_right_rate": verification_right_rate,
        "gate_pass_count": gate_pass,
        "gate_fail_count": gate_fail,
        "gate_skipped_count": gate_skipped,
        "gate_pass_rate": gate_pass_rate,
        "gate_ok": bool(gate_doc.get("ok")),
    }
