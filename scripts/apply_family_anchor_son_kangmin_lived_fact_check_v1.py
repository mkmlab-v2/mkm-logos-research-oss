#!/usr/bin/env python3
"""Apply kangmin son family_anchor fact-check session + clinical labs intake."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.apply_family_anchor_lived_fact_check_v1 import apply_session, _now, _read, _write  # noqa: E402

DEFAULT_SESSION = ROOT / "docs/final/artifacts/family_anchor_fact_check_session_son_kangmin_v1_latest.json"
DEFAULT_ANCHOR = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_son_kangmin_v1_latest.json"
DEFAULT_GUIDE = ROOT / "docs/final/artifacts/kangmin_son_integrated_guide_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/family_anchor_son_kangmin_fact_check_apply_latest.json"


def _merge_clinical_labs(anchor: dict[str, Any], session: dict[str, Any]) -> None:
    intake = session.get("clinical_labs_intake")
    if not isinstance(intake, dict):
        return

    height = intake.get("height_cm")
    weight = intake.get("weight_kg")
    bmi = intake.get("bmi_approx")
    labs_available = bool(intake.get("labs_numeric_available"))

    labs_block: dict[str, Any] = {
        "ssot": "pediatric_endocrinology_clinician",
        "as_of_kst": intake.get("anthropometrics_as_of_kst"),
        "labs_numeric_available": labs_available,
        "disclaimer_ko": "검사 수치·처방·예후는 주치의 SSOT; 본 anchor는 보호자 intake·생활 설계 참고만",
        "anthropometrics": {
            "height_cm": height,
            "weight_kg": weight,
            "bmi_approx": bmi,
            "source": "parent_commander_fact_check",
        },
        "labs": {
            "igf_1": {
                "status": "pending_clinician_ssot",
                "value": None,
                "unit": "ng/mL",
                "note_ko": "GH 재개 후 3·6개월 추적 — 주치의 일정",
            },
            "hba1c": {
                "status": "pending_clinician_ssot",
                "value": None,
                "unit": "%",
                "note_ko": "당 상승 이력(보호자 보고); 숫자는 EMR/검사지만",
            },
            "fasting_glucose": {
                "status": "pending_clinician_ssot",
                "value": None,
                "unit": "mg/dL",
            },
            "bone_age_years": {
                "status": "pending_clinician_ssot",
                "value": None,
                "unit": "years",
            },
        },
        "parent_reported_context_ko": intake.get("parent_reported_context_ko"),
        "pending_lab_keys": list(intake.get("labs_pending_clinician_ssot") or []),
    }

    anchor["clinical_labs_l0"] = labs_block

    clinical = anchor.setdefault("clinical_l0_parent_reported", {})
    if isinstance(clinical, dict):
        if height is not None:
            clinical["height_cm"] = height
        if weight is not None:
            clinical["weight_kg"] = weight
        if bmi is not None:
            clinical["bmi_approx"] = bmi
        clinical["anthropometrics_as_of_kst"] = intake.get("anthropometrics_as_of_kst")
        clinical["labs_numeric_available"] = labs_available


def _sync_guide_json(guide: dict[str, Any], anchor: dict[str, Any]) -> None:
    labs = anchor.get("clinical_labs_l0")
    if not isinstance(labs, dict):
        return
    guide["clinical_labs_l0"] = labs
    guide["fact_check_applied_at_utc"] = anchor.get("ts_utc")
    clinical = anchor.get("clinical_l0_parent_reported")
    if isinstance(clinical, dict):
        guide["clinical_l0_parent_reported"] = dict(clinical)


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply kangmin son family anchor lived fact-check.")
    ap.add_argument("--session-json", type=Path, default=DEFAULT_SESSION)
    ap.add_argument("--anchor-json", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--guide-json", type=Path, default=DEFAULT_GUIDE)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    session_path = args.session_json if args.session_json.is_absolute() else ROOT / args.session_json
    anchor_path = args.anchor_json if args.anchor_json.is_absolute() else ROOT / args.anchor_json
    guide_path = args.guide_json if args.guide_json.is_absolute() else ROOT / args.guide_json
    report_path = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json

    session = _read(session_path)
    anchor = _read(anchor_path)

    if session.get("anchor_id") != anchor.get("anchor_id"):
        raise SystemExit("anchor_id mismatch between session and anchor")

    updated_anchor, warnings = apply_session(session, anchor, allow_partial=False)
    updated_anchor["version"] = "1.1.0"
    _merge_clinical_labs(updated_anchor, session)

    resp_root = updated_anchor.setdefault("responses", {})
    if isinstance(resp_root, dict):
        resp_root["lived_fact_check_applied_at"] = _now()
        resp_root["operator_verdict_20260607_labs"] = (
            "height_weight_confirmed_lab_numeric_pending_clinician_ssot"
        )
        if session.get("operator_integrated_guide_helpful") is True:
            resp_root["operator_verdict_integrated_guide"] = "integrated_growth_guide_v1_matches"

    try:
        session_ref = str(session_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        session_ref = str(session_path)
    try:
        anchor_ref = str(anchor_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        anchor_ref = str(anchor_path)

    report: dict[str, Any] = {
        "schema": "family_anchor_son_kangmin_fact_check_apply_report_v1",
        "applied_at_utc": _now(),
        "dry_run": args.dry_run,
        "session_path": session_ref,
        "anchor_path": anchor_ref,
        "warnings": warnings,
        "labs_numeric_available": bool(
            (session.get("clinical_labs_intake") or {}).get("labs_numeric_available")
        ),
        "anthropometrics": {
            "height_cm": (session.get("clinical_labs_intake") or {}).get("height_cm"),
            "weight_kg": (session.get("clinical_labs_intake") or {}).get("weight_kg"),
        },
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    _write(session_path, session)
    _write(anchor_path, updated_anchor)
    if guide_path.is_file():
        guide = _read(guide_path)
        _sync_guide_json(guide, updated_anchor)
        _write(guide_path, guide)
    _write(report_path, report)
    print(f"applied -> {anchor_path}")
    print(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
