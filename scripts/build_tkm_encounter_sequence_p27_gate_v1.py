#!/usr/bin/env python3
"""TKM encounter_sequence P27 gate: L5 myeongni lens wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P26_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p26_gate_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
SEPARATION = ROOT / "reports/tkm_myeongni_sasang_lens_separation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p27_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p26 = _load(P26_GATE)
    myeongni = _load(MYEONGNI_KPI)
    separation = _load(SEPARATION)
    weekly = _load(WEEKLY)
    l5 = weekly.get("l5_myeongni_kpi") if isinstance(weekly.get("l5_myeongni_kpi"), dict) else {}
    gold = myeongni.get("physician_gold_only") if isinstance(myeongni.get("physician_gold_only"), dict) else {}

    checks = {
        "p26_gate_ok": {"passed": p26.get("gate_ok") is True},
        "myeongni_kpi_ok": {"passed": myeongni.get("kpi_ok") is True},
        "lens_separation_ok": {"passed": separation.get("separation_ok") is True},
        "weekly_l5_sync_ok": {"passed": l5.get("l5_myeongni_headline_ok") is True},
        "gold_sidecar_min_ok": {"passed": int(gold.get("myeongni_sidecar_count") or 0) >= 1},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p27_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p27_status": "myeongni_lens_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "myeongni_kpi_ref": str(MYEONGNI_KPI).replace("\\", "/"),
        "separation_ref": str(SEPARATION).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p27_chain_v1.py --with-p26-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p27_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
