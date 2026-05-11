#!/usr/bin/env python3
"""Audit consistency across VA trajectory, cooldown event, and fusion report.

B-track only, NON_GATING. Produces a single integrity report:
  reports/fusion_control_integrity_audit_latest.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VA = ROOT / "reports" / "va_trajectory_log_latest.json"
DEFAULT_COOLDOWN = ROOT / "reports" / "va_cooldown_event_log_latest.json"
DEFAULT_FUSION = ROOT / "reports" / "cross_lens_fusion_report_latest.json"
DEFAULT_OUT = ROOT / "reports" / "fusion_control_integrity_audit_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_audit(va_doc: dict[str, Any], cooldown_doc: dict[str, Any], fusion_doc: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    schema_ok = (
        str(va_doc.get("schema")) == "va_trajectory_log_v1"
        and str(cooldown_doc.get("schema")) == "va_cooldown_event_v1"
        and str(fusion_doc.get("schema")) == "cross_lens_fusion_report_v1"
    )
    checks.append(_check("schema_contracts", schema_ok, "va/cooldown/fusion schemas verified" if schema_ok else "schema mismatch"))

    va_sid = str(va_doc.get("session_id") or "")
    cd_sid = str(cooldown_doc.get("session_id") or "")
    fu_sid = str((fusion_doc.get("va_snapshot") or {}).get("session_id") or "")
    va_turn = int(va_doc.get("turn_index") or -1)
    cd_turn = int(cooldown_doc.get("turn_index") or -1)
    fu_turn = int((fusion_doc.get("va_snapshot") or {}).get("turn_index") or -1)
    aligned = va_sid == cd_sid == fu_sid and va_turn == cd_turn == fu_turn
    checks.append(
        _check(
            "session_turn_alignment",
            aligned,
            f"session_id {va_sid}|{cd_sid}|{fu_sid}, turn {va_turn}|{cd_turn}|{fu_turn}",
        )
    )

    va_cc = va_doc.get("cooldown_control")
    va_cc = va_cc if isinstance(va_cc, dict) else {}
    va_applied = bool(va_cc.get("applied"))
    cd_applied = bool(cooldown_doc.get("applied"))
    fu_applied = bool((fusion_doc.get("va_snapshot") or {}).get("cooldown_applied"))
    state_ok = va_applied == cd_applied == fu_applied
    checks.append(
        _check(
            "cooldown_state_alignment",
            state_ok,
            f"va={va_applied}, cooldown_event={cd_applied}, fusion={fu_applied}",
        )
    )

    va_pid = str(va_cc.get("policy_id") or "")
    cd_pid = str(cooldown_doc.get("policy_id") or "")
    fu_pid = str((fusion_doc.get("va_snapshot") or {}).get("cooldown_policy_id") or "")
    policy_ok = (not va_applied) or (va_pid == cd_pid == fu_pid and va_pid != "")
    checks.append(_check("cooldown_policy_alignment", policy_ok, f"policy_id {va_pid}|{cd_pid}|{fu_pid}"))

    va_reasons = sorted(str(x) for x in (va_cc.get("reasons") or []))
    cd_reasons = sorted(str(x) for x in (cooldown_doc.get("reasons") or []))
    fu_reasons = sorted(str(x) for x in ((fusion_doc.get("va_snapshot") or {}).get("cooldown_reasons") or []))
    reasons_ok = (not va_applied) or (va_reasons == cd_reasons == fu_reasons)
    checks.append(_check("cooldown_reasons_alignment", reasons_ok, f"reasons {va_reasons}|{cd_reasons}|{fu_reasons}"))

    rows = fusion_doc.get("candidates_ranked")
    rows = rows if isinstance(rows, list) else []
    detail_parts: list[str] = []
    fusion_ok = True
    if va_applied:
        for reason, required_rule in [
            ("high_arousal", "high_arousal_joy_energy_damp"),
            ("low_valence", "low_valence_caution_temperance_damp"),
        ]:
            if reason not in va_reasons:
                continue
            matched_rows = [r for r in rows if required_rule in (r.get("cooldown_damp_rules_applied") or [])]
            if not matched_rows:
                fusion_ok = False
                detail_parts.append(f"missing rule row: {required_rule}")
                continue
            bad_rows = [
                r
                for r in matched_rows
                if not bool(r.get("cooldown_fusion_damp_applied")) or float(r.get("cooldown_damp_factor") or 1.0) >= 1.0
            ]
            if bad_rows:
                fusion_ok = False
                detail_parts.append(f"invalid damp fields for {required_rule}")
    detail = "; ".join(detail_parts) if detail_parts else "required damp rules present and damp factors < 1"
    checks.append(_check("fusion_rule_application", fusion_ok, detail))

    passed = sum(1 for c in checks if c["pass"])
    failed = len(checks) - passed
    return {
        "schema": "fusion_control_integrity_audit_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": ["NON_GATING", "ADVISORY_ONLY", "B_TRACK_RESEARCH"],
        "sources": {
            "va_trajectory_json": "inline_or_cli",
            "cooldown_event_json": "inline_or_cli",
            "fusion_report_json": "inline_or_cli",
        },
        "checks": checks,
        "summary": {"all_pass": failed == 0, "passed": passed, "failed": failed},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--va-trajectory-json", type=Path, default=DEFAULT_VA)
    ap.add_argument("--cooldown-event-json", type=Path, default=DEFAULT_COOLDOWN)
    ap.add_argument("--fusion-report-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    va_doc = _read_json(args.va_trajectory_json)
    cooldown_doc = _read_json(args.cooldown_event_json)
    fusion_doc = _read_json(args.fusion_report_json)
    report = build_audit(va_doc, cooldown_doc, fusion_doc)
    report["sources"] = {
        "va_trajectory_json": args.va_trajectory_json.as_posix(),
        "cooldown_event_json": args.cooldown_event_json.as_posix(),
        "fusion_report_json": args.fusion_report_json.as_posix(),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["summary"]["all_pass"], "failed": report["summary"]["failed"], "out": str(args.out)}, indent=2))
    return 0 if report["summary"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
