#!/usr/bin/env python3
"""TKM encounter_sequence P36 gate: disagreement × conflict resolver cross [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P35_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p36_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p35 = _load(P35_GATE)
    cross = _load(CROSS)
    weekly = _load(WEEKLY)
    dr = weekly.get("disagreement_resolver_cross_kpi") if isinstance(weekly.get("disagreement_resolver_cross_kpi"), dict) else {}

    checks = {
        "p35_gate_ok": {"passed": p35.get("gate_ok") is True},
        "disagreement_resolver_cross_kpi_ok": {"passed": cross.get("kpi_ok") is True},
        "disagreement_resolver_non_gating": {"passed": cross.get("non_gating") is True},
        "curated_learning_pointer_ok": {"passed": int(cross.get("curated_learning_pointer_count") or 0) >= 1},
        "weekly_disagreement_cross_sync_ok": {"passed": dr.get("disagreement_resolver_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p36_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p36_status": "disagreement_resolver_cross_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "disagreement_count": cross.get("disagreement_count"),
        "disagreement_lens_conflict_cross_rate": cross.get("disagreement_lens_conflict_cross_rate"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p36_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p36_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
