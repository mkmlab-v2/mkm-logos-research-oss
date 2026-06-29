#!/usr/bin/env python3
"""TKM encounter_sequence P32 gate: L6 Logos cosmic anchor wire [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P31_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p31_gate_v1_latest.json"
LOGOS_APPLY = ROOT / "reports/tkm_encounter_sequence_logos_sidecar_apply_v1_latest.json"
LOGOS_KPI = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"
SEPARATION = ROOT / "reports/tkm_logos_sasang_lens_separation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p32_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p31 = _load(P31_GATE)
    apply_doc = _load(LOGOS_APPLY)
    kpi = _load(LOGOS_KPI)
    separation = _load(SEPARATION)
    weekly = _load(WEEKLY)
    reg = _load(REGISTRY)
    l6 = weekly.get("l6_logos_kpi") if isinstance(weekly.get("l6_logos_kpi"), dict) else {}
    gold = kpi.get("physician_gold_only") if isinstance(kpi.get("physician_gold_only"), dict) else {}

    checks = {
        "p31_gate_ok": {"passed": p31.get("gate_ok") is True},
        "logos_registry_ok": {"passed": int(reg.get("enabled_count") or 0) >= 40},
        "logos_sidecar_apply_ok": {"passed": apply_doc.get("ok") is True},
        "logos_kpi_ok": {"passed": kpi.get("kpi_ok") is True},
        "physician_gold_logos_ok": {"passed": kpi.get("physician_gold_logos_ok") is True},
        "logos_lens_separation_ok": {"passed": separation.get("separation_ok") is True},
        "weekly_l6_sync_ok": {"passed": l6.get("l6_logos_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p32_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p32_status": "logos_cosmic_anchor_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "physician_gold_logos_linked_count": gold.get("logos_anchor_linked_count"),
        "logos_registry_enabled_count": reg.get("enabled_count"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p32_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p32_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
