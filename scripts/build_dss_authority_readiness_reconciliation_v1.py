#!/usr/bin/env python3
"""Reconcile DSS authority_readiness ext3 pin vs latest unified frontline cycle output."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXT3 = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
DEFAULT_REFRESH = (
    ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260607_ext3_refresh.json"
)
DEFAULT_FRONTLINE = ROOT / "projects/dss-4d-ingest/outputs/frontline_latest_status.json"
DEFAULT_OUT = ROOT / "reports/dss_authority_readiness_reconciliation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_status_from_output(text: str) -> str | None:
    m = re.search(r"status=(READY|BLOCKED|WATCH|PASS|FAIL)", text, re.I)
    return m.group(1).upper() if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ext3-authority-json", type=Path, default=DEFAULT_EXT3)
    ap.add_argument("--refreshed-authority-json", type=Path, default=DEFAULT_REFRESH)
    ap.add_argument("--frontline-status-json", type=Path, default=DEFAULT_FRONTLINE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ext3_status = "MISSING"
    ext3_checks: dict[str, Any] = {}
    if args.ext3_authority_json.is_file():
        ext3 = _load(args.ext3_authority_json)
        ext3_status = str(ext3.get("status") or "UNKNOWN").upper()
        ext3_checks = ext3.get("checks") if isinstance(ext3.get("checks"), dict) else {}

    cycle_tag = None
    cycle_report_path: Path | None = None
    cycle_authority_status = None
    frontline_overall = None
    if args.frontline_status_json.is_file():
        front = _load(args.frontline_status_json)
        cycle_tag = front.get("latest_cycle_tag")
        frontline_overall = front.get("overall_status")
        rel = str(front.get("latest_cycle_report") or "").replace("\\", "/")
        if rel:
            cycle_report_path = ROOT / "projects/dss-4d-ingest" / rel
            if cycle_report_path.is_file():
                cycle = _load(cycle_report_path)
                runs = cycle.get("runs") if isinstance(cycle.get("runs"), dict) else {}
                auth_step = runs.get("authority_readiness") if isinstance(runs.get("authority_readiness"), dict) else {}
                cycle_authority_status = _parse_status_from_output(str(auth_step.get("output") or ""))

    ndjson_candidates = [
        ROOT / "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
        ROOT / "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext2_weighted.ndjson",
        ROOT / "projects/dss-4d-ingest/outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson",
    ]
    dss_ndjson = ROOT / "projects/dss-4d-ingest/outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson"
    dss_pilot_ndjson = ROOT / "projects/dss-4d-ingest/outputs/dss_tokens_pilot_manifest_tf4.ndjson"
    ndjson_present = [str(p) for p in ndjson_candidates if p.is_file()]
    dss_record_count = _load_jsonl_record_count(dss_ndjson) if dss_ndjson.is_file() else 0
    dss_pilot_record_count = _load_jsonl_record_count(dss_pilot_ndjson) if dss_pilot_ndjson.is_file() else 0

    ingest_recommendation = "WATCH"
    if ext3_status == "READY" and ndjson_present:
        ingest_recommendation = "MANIFEST_SUMMARY"
    elif ext3_status == "READY":
        ingest_recommendation = "WATCH_MISSING_NDJSON"
    elif cycle_authority_status == "BLOCKED":
        ingest_recommendation = "BLOCKED_CYCLE_AUTHORITY"

    refresh_status = None
    refresh_path: Path | None = None
    if args.refreshed_authority_json.is_file():
        refresh_path = args.refreshed_authority_json
        refresh_status = str(_load(refresh_path).get("status") or "UNKNOWN").upper()

    aligned = ext3_status == cycle_authority_status if cycle_authority_status else None
    pin_policy_path = ROOT / "reports/dss_authority_pin_policy_research_v1_latest.json"
    policy_aligned_for_ingest = ext3_status == "READY" and ingest_recommendation == "MANIFEST_SUMMARY"
    payload = {
        "schema": "dss_authority_readiness_reconciliation_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "ext3_pin": {
            "path": str(args.ext3_authority_json),
            "status": ext3_status,
            "checks": ext3_checks,
        },
        "frontline_cycle": {
            "path": str(args.frontline_status_json),
            "latest_cycle_tag": cycle_tag,
            "overall_status": frontline_overall,
            "cycle_report_path": str(cycle_report_path) if cycle_report_path else None,
            "authority_readiness_status_parsed": cycle_authority_status,
        },
        "frontline_cycle_refresh": {
            "path": str(refresh_path) if refresh_path else None,
            "authority_readiness_status": refresh_status,
            "note": "Local re-eval via evaluate_authority_readiness.py; historical cycle report unchanged.",
        },
        "reconciliation": {
            "ext3_vs_cycle_authority_aligned": aligned,
            "policy_aligned_for_ingest": policy_aligned_for_ingest,
            "pin_policy_path": str(pin_policy_path),
            "ingest_gate_ssot": "ext3_hebrew_priority_pin",
            "cycle_historical_ssot": "unified_frontline_cycle_authority_readiness",
            "note": (
                "ext3 Hebrew-priority pilot pin governs manifest-summary ingest; "
                "cycle authority_readiness BLOCKED is pre-ext3 historical baseline — see pin policy."
            ),
        },
        "ndjson_manifest": {
            "files_present": ndjson_present,
            "files_present_count": len(ndjson_present),
            "dss_leg_record_count": dss_record_count,
            "dss_pilot_record_count": dss_pilot_record_count,
            "dss_leg_smoke_likely": dss_record_count > 0 and dss_record_count <= 5,
            "smoke_bootstrap_likely": len(ndjson_present) > 0 and all(
                _load_jsonl_record_count(p) <= 5 for p in ndjson_candidates if p.is_file()
            ),
        },
        "ingest_recommendation": ingest_recommendation,
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "ingest_recommendation": ingest_recommendation}, ensure_ascii=False))
    return 0


def _load_jsonl_record_count(path: Path) -> int:
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


if __name__ == "__main__":
    raise SystemExit(main())
