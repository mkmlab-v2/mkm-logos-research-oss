#!/usr/bin/env python3
"""Customer-masked intake lane readiness — drop file + provenance + n30 [HYPO]."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTAKE_DIR = ROOT / "data/wtt/intake"
ACTIVE_TENANT = ROOT / "docs/final/artifacts/wtt_pilot_active_tenant_v1_latest.json"
HUMAN_GATE = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
OPERATOR_GATE = ROOT / "reports/wtt_operator_panel_gate_v1_latest.json"
DROP_STATE = ROOT / "reports/wtt_pilot_intake_drop_watch_state_v1.json"
TEMPLATE = ROOT / "data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl"
DEFAULT_OUT = ROOT / "reports/wtt_customer_intake_readiness_v1_latest.json"
TASK_NAME = "MKM_WttPilot_IntakeDropWatch"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,48}[a-z0-9]$")
INTERNAL_STEMS = frozenset(
    {
        "wtt-operator-panel-v1",
        "wtt-customer-stub-v1",
        "wtt-solo-internal-v1",
        "wtt-synthetic-spicy-v1",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _scheduled_task_registered() -> bool:
    proc = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _scan_intake_candidates() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not INTAKE_DIR.is_dir():
        return out
    for path in sorted(INTAKE_DIR.glob("*.jsonl")):
        if path.name.startswith("wtt_pilot_"):
            continue
        stem = path.stem
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        customer_rows = 0
        issues: list[str] = []
        for i, line in enumerate(lines, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(f"line_{i}_json:{exc}")
                continue
            if row.get("customer_provided") is True:
                customer_rows += 1
            labels = set(row.get("labels") or [])
            if labels & {"pilot_fill_template", "synthetic_spicy", "synthetic_stub", "operator_panel"}:
                issues.append(f"line_{i}_forbidden_lane_labels")
        if stem in INTERNAL_STEMS:
            issues.append("internal_lane_tenant")
        if not SLUG_RE.match(stem):
            issues.append("filename_not_tenant_slug")
        if len(lines) < 20:
            issues.append(f"session_count_lt_20:{len(lines)}")
        if customer_rows == 0:
            issues.append("no_customer_provided_rows")
        out.append(
            {
                "path": path.as_posix(),
                "tenant_id": stem,
                "session_count": len(lines),
                "customer_provided_rows": customer_rows,
                "eligible_for_customer_auto_intake": len(issues) == 0,
                "issues": issues,
            }
        )
    return out


def build_report() -> dict[str, Any]:
    human = _load(HUMAN_GATE) or {}
    operator = _load(OPERATOR_GATE) or {}
    active = _load(ACTIVE_TENANT) or {}
    candidates = _scan_intake_candidates()
    eligible = [c for c in candidates if c["eligible_for_customer_auto_intake"]]
    drop_registered = _scheduled_task_registered()
    template_exists = TEMPLATE.is_file()
    fill_placeholders = 0
    if template_exists:
        for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
            if "[FILL:" in line:
                fill_placeholders += 1

    blockers: list[str] = []
    if not eligible:
        blockers.append("no_eligible_customer_jsonl_in_data_wtt_intake")
    if human.get("human_n30_gate_met") is not True:
        blockers.append("human_n30_gate_not_met")
    if not drop_registered:
        blockers.append("drop_watch_task_not_registered")

    human_met = human.get("human_n30_gate_met") is True
    if human_met and eligible:
        next_actions = [
            "Premium CS closure: scripts/Invoke-WttPremiumCsClosure_v1.ps1",
            "Cross-lane status: py scripts/build_wtt_premium_cs_cross_lane_status_v1.py",
            "Stress deck: reports/wtt_stress_certified_deck_v1_latest.md",
            "SEND HOLD until counsel + real recruited provenance (not curated research_only)",
        ]
    else:
        next_actions = [
            "Fill Premium CS template: data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl",
            "Copy to data/wtt/intake/<tenant-slug>.jsonl (customer_provided=true, >=20 sessions)",
            "Run human gate: scripts/Invoke-WttHumanGateRoutine_v1.ps1 -Lane customer (consent evidence)",
            "Drop watch auto: scripts/Invoke-WttPilotIntakeAuto_v1.ps1 or scheduled drop watch",
        ]

    return {
        "schema": "wtt_customer_intake_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "operator_panel_separate": {
            "gate_met": operator.get("operator_panel_n30_gate_met"),
            "sessions": operator.get("operator_panel_sessions_collected"),
            "not_eligible_for_send": operator.get("not_eligible_for_send", True),
        },
        "human_n30": {
            "gate_met": human.get("human_n30_gate_met"),
            "sessions_collected": human.get("human_sessions_collected"),
            "enrollment_ready": human.get("enrollment_ready"),
        },
        "active_tenant": {
            "tenant_id": active.get("tenant_id"),
            "session_jsonl": active.get("session_jsonl"),
            "icp": active.get("icp"),
        },
        "drop_watch": {
            "task_name": TASK_NAME,
            "task_registered": drop_registered,
            "state_path": DROP_STATE.as_posix() if DROP_STATE.is_file() else None,
        },
        "premium_cs_template": {
            "path": TEMPLATE.as_posix(),
            "exists": template_exists,
            "rows_with_fill_placeholder": fill_placeholders,
        },
        "intake_candidates": candidates,
        "eligible_customer_intake_count": len(eligible),
        "customer_lane_ready_for_auto_intake": len(eligible) > 0 and len(blockers) == 0,
        "premium_cs_closure_one_click": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPremiumCsClosure_v1.ps1",
        "blockers": blockers,
        "next_actions": next_actions,
        "one_click_prep": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttCustomerLanePrep_v1.ps1",
        "note_ko": "operator panel 30/30과 분리. 실고객 JSONL+provenance 없으면 SEND HOLD 유지.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if no eligible customer intake file.")
    args = ap.parse_args()
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = report["eligible_customer_intake_count"] > 0 or not args.strict
    print(
        json.dumps(
            {
                "ok": ok,
                "eligible": report["eligible_customer_intake_count"],
                "human_n30_gate_met": report["human_n30"]["gate_met"],
                "drop_watch_registered": report["drop_watch"]["task_registered"],
                "blockers": report["blockers"],
            }
        )
    )
    if args.strict and report["eligible_customer_intake_count"] == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
