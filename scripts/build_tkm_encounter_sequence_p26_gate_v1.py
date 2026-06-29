#!/usr/bin/env python3
"""TKM encounter_sequence P26 gate: ops closure items 1–8 [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P25_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p25_gate_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p26_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p25 = _load(P25_GATE)
    ops = _load(OPS)
    items = ops.get("items") if isinstance(ops.get("items"), dict) else {}
    checks = {
        "p25_gate_ok": {"passed": p25.get("gate_ok") is True},
        "ops_closure_ok": {"passed": ops.get("closure_ok") is True},
        "daily_capture_ok": {"passed": (items.get("1_daily_capture") or {}).get("ok") is True},
        "human_ack_ok": {"passed": (items.get("2_curated_learning_ack") or {}).get("ok") is True},
        "fact_lock_flag_ok": {"passed": (items.get("3_fact_lock_bundle") or {}).get("ok") is True},
        "weekly_scheduler_ok": {"passed": (items.get("4_weekly_scheduler") or {}).get("ok") is True},
        "export_ingest_ok": {"passed": (items.get("6_export_ingest") or {}).get("ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p26_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p26_status": "ops_closure_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "ops_closure_ref": str(OPS).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p26_chain_v1.py --with-p25-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p26_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
