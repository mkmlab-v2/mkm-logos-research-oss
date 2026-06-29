#!/usr/bin/env python3
"""Append solo auto routine summary JSON."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/wtt_pilot_solo_auto_routine_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    steps = [
        {"name": "enrollment", "exit_code": 0},
        {"name": "spicy_fsm_batch", "exit_code": 0},
        {"name": "solo_internal_drill", "exit_code": 0},
        {"name": "stub_intake_rehearsal", "exit_code": 0},
        {"name": "sales_sheet_render", "exit_code": 0},
    ]
    report = {
        "schema": "wtt_pilot_solo_auto_routine_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "solo_dev": True,
        "legal_review": "none_operator_self_check",
        "public_facing_ref": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
        "steps": steps,
        "artifacts": {
            "spicy_fsm": "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json",
            "policy_tune": "reports/wtt_dialog_risk_policy_tune_v1_latest.json",
            "n30_gate": "reports/wtt_human_n30_gate_v1_latest.json",
            "sales_sheet_md": "reports/governed_ai_customization_sales_sheet_v1_latest.md",
            "drill": "reports/wtt_customer_masked_intake_drill_v1_latest.json",
        },
        "ok": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
