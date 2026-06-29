#!/usr/bin/env python3
"""TKM encounter_sequence P38 gate: export/ingest live + disagreement backfill [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P37_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p37_gate_v1_latest.json"
EXPORT_KPI = ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json"
DISAGREEMENT = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p38_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p37 = _load(P37_GATE)
    export_kpi = _load(EXPORT_KPI)
    disagreement = _load(DISAGREEMENT)
    weekly = _load(WEEKLY)
    ei = weekly.get("export_ingest_kpi") if isinstance(weekly.get("export_ingest_kpi"), dict) else {}

    wired = int(disagreement.get("disagreement_resolver_wired_count") or 0)
    total = int(disagreement.get("disagreement_count") or 0)
    wired_rate = round(wired / total, 4) if total else None

    checks = {
        "p37_gate_ok": {"passed": p37.get("gate_ok") is True},
        "export_ingest_live_ok": {"passed": export_kpi.get("live_ingest_ok") is True},
        "export_ingest_lens_stack_ok": {"passed": export_kpi.get("lens_stack_ok") is True},
        "disagreement_resolver_wired_ok": {"passed": wired >= 1},
        "disagreement_wired_rate_ok": {"passed": isinstance(wired_rate, (int, float)) and float(wired_rate) >= 0.5},
        "weekly_export_ingest_sync_ok": {"passed": ei.get("export_ingest_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p38_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p38_status": "export_ingest_live_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "disagreement_resolver_wired_rate": wired_rate,
        "reproduce": "py scripts/run_tkm_encounter_sequence_p38_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p38_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
