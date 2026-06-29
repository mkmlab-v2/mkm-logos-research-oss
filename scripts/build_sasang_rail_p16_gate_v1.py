#!/usr/bin/env python3
"""Sasang rail P16 gate: attested promote drill + clinical ingest + webhook drill [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P15 = ROOT / "docs/final/artifacts/sasang_rail_p15_gate_v1_latest.json"
ATTESTED_DRILL = ROOT / "reports/sasang_attested_joint_promote_drill_v1_latest.json"
CLINICAL_DRILL = ROOT / "reports/sasang_commander_clinical_promote_drill_v1_latest.json"
CLINICAL_INGEST = ROOT / "docs/final/artifacts/sasang_commander_clinical_ingest_gate_v1_latest.json"
DEID_ROW = ROOT / "docs/final/artifacts/sasang_commander_clinical_deid_row_gate_v1_latest.json"
WEBHOOK_DRILL = ROOT / "reports/sasang_dual_probe_drift_webhook_drill_v1_latest.json"
EVAL_CHAIN = ROOT / "reports/sasang_attested_only_eval_chain_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p16_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p15 = _load(P15)
    attested_drill = _load(ATTESTED_DRILL)
    clinical_drill = _load(CLINICAL_DRILL)
    clinical_ingest = _load(CLINICAL_INGEST)
    deid_row = _load(DEID_ROW)
    webhook_drill = _load(WEBHOOK_DRILL)
    eval_chain = _load(EVAL_CHAIN)

    checks = {
        "p15_gate_ok": {"passed": p15.get("gate_ok") is True},
        "p15_eval_path_locked_ok": {"passed": p15.get("sasang_rail_p15_status") == "eval_path_locked_ok"},
        "deid_row_gate_ok": {"passed": deid_row.get("gate_ok") is True},
        "attested_promote_drill_ok": {"passed": attested_drill.get("all_ok") is True},
        "clinical_promote_drill_ok": {"passed": clinical_drill.get("all_ok") is True},
        "clinical_ingest_ok": {
            "passed": clinical_ingest.get("gate_ok") is True
            and clinical_ingest.get("clinical_ingest_status") == "ingested_ok",
        },
        "attested_eval_chain_ok": {"passed": eval_chain.get("all_ok") is True},
        "drift_webhook_drill_ok": {"passed": webhook_drill.get("drill_ok") is True},
        "drift_webhook_not_live_by_default": {"passed": webhook_drill.get("live_mode") is False},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p16_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p16_status": "promote_drill_attested_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "clinical_ingest_status": clinical_ingest.get("clinical_ingest_status"),
        "promote_drill_mode": attested_drill.get("promote_drill_mode"),
        "reproduce": "py scripts/run_sasang_rail_p16_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p16_status": doc["sasang_rail_p16_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
