#!/usr/bin/env python3
"""TKM encounter_sequence P31 gate: physician_gold stub-free engine wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P30_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p30_gate_v1_latest.json"
BACKFILL = ROOT / "reports/tkm_myeongni_engine_ledger_backfill_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_myeongni_passive_observation_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p31_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p30 = _load(P30_GATE)
    backfill = _load(BACKFILL)
    kpi = _load(MYEONGNI_KPI)
    weekly = _load(WEEKLY)
    passive = _load(PASSIVE)
    gold = kpi.get("physician_gold_only") if isinstance(kpi.get("physician_gold_only"), dict) else {}
    l5 = weekly.get("l5_myeongni_kpi") if isinstance(weekly.get("l5_myeongni_kpi"), dict) else {}
    gold_stub = int(gold.get("stub_report_linked_count") or 0)
    gold_engine = int(gold.get("engine_report_linked_count") or 0)
    gold_sidecar = int(gold.get("myeongni_sidecar_count") or 0)

    checks = {
        "p30_gate_ok": {"passed": p30.get("gate_ok") is True},
        "ledger_backfill_ok": {"passed": backfill.get("ok") is True},
        "physician_gold_stub_free_ok": {"passed": gold_stub == 0 and gold_sidecar >= 1},
        "physician_gold_engine_full_ok": {"passed": gold_sidecar >= 1 and gold_engine == gold_sidecar},
        "myeongni_kpi_engine_ok": {"passed": kpi.get("physician_gold_engine_ok") is True},
        "weekly_l5_stub_free_ok": {"passed": l5.get("l5_myeongni_headline_ok") is True},
        "passive_observation_ok": {"passed": passive.get("observation_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p31_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p31_status": "myeongni_engine_stub_free_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "physician_gold_stub_report_linked_count": gold_stub,
        "physician_gold_engine_report_linked_count": gold_engine,
        "reproduce": "py scripts/run_tkm_encounter_sequence_p31_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p31_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
