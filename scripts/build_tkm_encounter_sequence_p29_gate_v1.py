#!/usr/bin/env python3
"""TKM encounter_sequence P29 gate: L0 red-flag router wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P28_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p28_gate_v1_latest.json"
L0_APPLY = ROOT / "reports/tkm_encounter_sequence_l0_apply_v1_latest.json"
L0_KPI = ROOT / "reports/tkm_encounter_sequence_l0_kpi_v1_latest.json"
SEPARATION = ROOT / "reports/tkm_l0_sasang_lens_separation_v1_latest.json"
SUMMARY = ROOT / "reports/encounter_sequence_summary_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
L0_TEMPLATE = ROOT / "docs/final/templates/l0_red_flag_escalation_ko_v1.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p29_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p28 = _load(P28_GATE)
    apply_doc = _load(L0_APPLY)
    l0 = _load(L0_KPI)
    separation = _load(SEPARATION)
    summary = _load(SUMMARY)
    weekly = _load(WEEKLY)
    l0k = weekly.get("l0_safety_kpi") if isinstance(weekly.get("l0_safety_kpi"), dict) else {}
    all_ledger = l0.get("all_ledger") if isinstance(l0.get("all_ledger"), dict) else {}

    checks = {
        "p28_gate_ok": {"passed": p28.get("gate_ok") is True},
        "l0_template_ok": {"passed": L0_TEMPLATE.is_file()},
        "l0_apply_ok": {"passed": apply_doc.get("ok") is True},
        "l0_kpi_ok": {"passed": l0.get("kpi_ok") is True},
        "l0_separation_ok": {"passed": separation.get("separation_ok") is True},
        "summary_l0_triggers_ok": {"passed": int(summary.get("l0_red_flag_trigger_events") or 0) >= 1},
        "weekly_l0_sync_ok": {"passed": l0k.get("l0_safety_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p29_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p29_status": "l0_router_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "l0_router_wired_count": all_ledger.get("l0_router_wired_count"),
        "l0_summary_trigger_events": all_ledger.get("l0_summary_trigger_events"),
        "l0_kpi_ref": str(L0_KPI).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p29_chain_v1.py --with-p28-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p29_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
