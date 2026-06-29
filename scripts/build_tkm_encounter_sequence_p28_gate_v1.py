#!/usr/bin/env python3
"""TKM encounter_sequence P28 gate: myeongni cross-check engine wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P27_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p27_gate_v1_latest.json"
CROSS_REFRESH = ROOT / "reports/tkm_encounter_sequence_myeongni_cross_refresh_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
DAILY_CAPTURE = ROOT / "reports/tkm_physician_gold_daily_capture_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p28_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p27 = _load(P27_GATE)
    cross = _load(CROSS_REFRESH)
    myeongni = _load(MYEONGNI_KPI)
    daily = _load(DAILY_CAPTURE)
    weekly = _load(WEEKLY)
    all_ledger = myeongni.get("all_ledger") if isinstance(myeongni.get("all_ledger"), dict) else {}
    l5 = weekly.get("l5_myeongni_kpi") if isinstance(weekly.get("l5_myeongni_kpi"), dict) else {}

    computed = int(all_ledger.get("cross_check_computed_count") or 0)
    checks = {
        "p27_gate_ok": {"passed": p27.get("gate_ok") is True},
        "cross_refresh_ok": {"passed": cross.get("ok") is True},
        "cross_check_computed_ok": {"passed": computed >= 1},
        "myeongni_kpi_ok": {"passed": myeongni.get("kpi_ok") is True},
        "daily_capture_ran_ok": {"passed": daily.get("ok") is True},
        "weekly_l5_sync_ok": {"passed": l5.get("l5_myeongni_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p28_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p28_status": "myeongni_cross_check_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "cross_check_computed_count": computed,
        "cross_check_status_counts": all_ledger.get("cross_check_status_counts"),
        "cross_refresh_ref": str(CROSS_REFRESH).replace("\\", "/"),
        "myeongni_kpi_ref": str(MYEONGNI_KPI).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p28_chain_v1.py --with-p27-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p28_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
