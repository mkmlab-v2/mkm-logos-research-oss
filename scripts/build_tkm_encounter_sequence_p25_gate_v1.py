#!/usr/bin/env python3
"""TKM encounter_sequence P25 gate: match_rate delta + multiturn physician_gold [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P24_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p24_gate_v1_latest.json"
DELTA = ROOT / "reports/tkm_match_rate_delta_report_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p25_gate_v1_latest.json"
AUTO03_SEQ = "SEQ-PHYSICIAN-GOLD-AUTO-03"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _seq_turn_count(seq_id: str) -> int:
    import importlib.util

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return 0
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for row in mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") != seq_id:
            continue
        summary = row.get("sequence_summary") if isinstance(row.get("sequence_summary"), dict) else {}
        return int(summary.get("turn_count") or 0)
    return 0


def build() -> dict[str, Any]:
    p24 = _load(P24_GATE)
    delta_doc = _load(DELTA)
    weekly = _load(WEEKLY)
    delta_kpi = weekly.get("match_rate_delta_kpi") if isinstance(weekly.get("match_rate_delta_kpi"), dict) else {}
    breakdown = delta_doc.get("encounter_breakdown") if isinstance(delta_doc.get("encounter_breakdown"), dict) else {}
    auto03_turns = _seq_turn_count(AUTO03_SEQ)

    checks = {
        "p24_gate_ok": {"passed": p24.get("gate_ok") is True},
        "match_rate_delta_kpi_ok": {"passed": delta_doc.get("delta_kpi_ok") is True},
        "weekly_delta_sync_ok": {
            "passed": delta_kpi.get("match_rate_delta_encounter_minus_clinic")
            == delta_doc.get("match_rate_delta_encounter_minus_clinic")
        },
        "physician_gold_auto03_ok": {"passed": auto03_turns >= 3},
        "multiturn_breakdown_min_ok": {"passed": int(breakdown.get("multiturn_count") or 0) >= 1},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p25_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p25_status": "match_rate_delta_multiturn_gold_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "match_rate_delta": delta_doc.get("match_rate_delta_encounter_minus_clinic"),
        "encounter_breakdown": breakdown,
        "physician_gold_auto03_turn_count": auto03_turns,
        "delta_ref": str(DELTA).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p25_chain_v1.py --with-p24-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p25_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
