#!/usr/bin/env python3
"""Summarize WTT full auto routine from disk gate artifacts [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/wtt_pilot_full_auto_routine_v1_latest.json"

GATES = {
    "human_n30": ROOT / "reports/wtt_human_n30_gate_v1_latest.json",
    "operator_panel": ROOT / "reports/wtt_operator_panel_gate_v1_latest.json",
    "spicy_fsm": ROOT / "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json",
    "operator_fsm": ROOT / "reports/wtt_operator_panel_fsm_batch_v1_latest.json",
    "operator_observe": ROOT / "reports/wtt_operator_panel_policy_observe_v1_latest.json",
    "stress_deck_md": ROOT / "reports/wtt_stress_certified_deck_v1_latest.md",
    "policy_tune": ROOT / "reports/wtt_dialog_risk_policy_tune_v1_latest.json",
    "customer_fsm": ROOT / "reports/wtt_tenant_fsm_batch_wtt-customer-live-v1_v1_latest.json",
    "compression_bridge": ROOT / "reports/wtt_compression_bridge_export_v1_latest.json",
    "cross_lane_status": ROOT / "reports/wtt_premium_cs_cross_lane_status_v1_latest.json",
    "customer_readiness": ROOT / "reports/wtt_customer_intake_readiness_v1_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    human = _load_optional(GATES["human_n30"]) or {}
    op = _load_optional(GATES["operator_panel"]) or {}
    spicy = _load_optional(GATES["spicy_fsm"]) or {}
    op_fsm = _load_optional(GATES["operator_fsm"]) or {}
    cust_fsm = _load_optional(GATES["customer_fsm"]) or {}
    cross_lane = _load_optional(GATES["cross_lane_status"]) or {}
    readiness = _load_optional(GATES["customer_readiness"]) or {}

    report = {
        "schema": "wtt_pilot_full_auto_routine_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "solo_dev": True,
        "one_click": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPilotFullAutoRoutine_v1.ps1",
        "gates": {
            "human_n30_gate_met": human.get("human_n30_gate_met"),
            "human_sessions_collected": human.get("human_sessions_collected"),
            "operator_panel_n30_gate_met": op.get("operator_panel_n30_gate_met"),
            "operator_panel_sessions_collected": op.get("operator_panel_sessions_collected"),
            "not_eligible_for_send": op.get("not_eligible_for_send", True),
        },
        "fsm": {
            "spicy_session_count": spicy.get("session_count"),
            "spicy_fsm_state_counts": spicy.get("fsm_state_counts"),
            "operator_session_count": op_fsm.get("session_count"),
            "operator_fsm_state_counts": op_fsm.get("fsm_state_counts"),
            "customer_session_count": cust_fsm.get("session_count"),
            "customer_fsm_state_counts": cust_fsm.get("fsm_state_counts"),
        },
        "customer_lane": {
            "tenant_id": cross_lane.get("wtt_lane", {}).get("tenant_id") or "wtt-customer-live-v1",
            "human_n30_gate_met": human.get("human_n30_gate_met"),
            "human_sessions_collected": human.get("human_sessions_collected"),
            "curated_pilot": True,
            "compression_bridge_rows": cross_lane.get("compression_lane", {}).get("bridge_row_count"),
            "readiness_blockers": readiness.get("blockers") or [],
        },
        "artifacts": {k: v.as_posix() for k, v in GATES.items() if v.is_file()},
        "note_ko": (
            "풀 오토: enrollment + operator panel 30/30 + premium CS curated 30/30 + stress deck. "
            "SEND·실모집 패널 주장은 HOLD."
        ),
        "ok": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "human_n30": report["gates"]["human_sessions_collected"],
                "operator_panel": report["gates"]["operator_panel_sessions_collected"],
                "out": str(args.out.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
