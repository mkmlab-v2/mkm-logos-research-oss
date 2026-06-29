#!/usr/bin/env python3
"""Sasang rail P15 gate: eval path locked + archive snapshot + drift webhook stub [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P14 = ROOT / "docs/final/artifacts/sasang_rail_p14_gate_v1_latest.json"
EVAL_PATH = ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_gate_v1_latest.json"
EVAL_CHAIN = ROOT / "reports/sasang_attested_only_eval_chain_v1_latest.json"
ARCHIVE_SNAP = ROOT / "reports/sasang_dummy_archive_weekly_snapshot_v1_latest.json"
WEBHOOK_STUB = ROOT / "reports/sasang_4agent_dual_probe_drift_webhook_stub_v1_latest.json"
CLINICAL_PENDING = ROOT / "docs/final/artifacts/sasang_commander_clinical_pending_gate_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_p15_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p14 = _load(P14)
    eval_path = _load(EVAL_PATH)
    eval_chain = _load(EVAL_CHAIN)
    archive = _load(ARCHIVE_SNAP)
    webhook = _load(WEBHOOK_STUB)
    clinical = _load(CLINICAL_PENDING)

    checks = {
        "p14_gate_ok": {"passed": p14.get("gate_ok") is True},
        "p14_mainline_eval_ok": {"passed": p14.get("sasang_rail_p14_status") == "mainline_eval_ok"},
        "eval_path_policy_ok": {
            "passed": eval_path.get("gate_ok") is True
            and eval_path.get("eval_path_status") == "attested_default_locked",
        },
        "attested_eval_chain_ok": {"passed": eval_chain.get("all_ok") is True},
        "archive_weekly_snapshot_ok": {"passed": archive.get("snapshot_ok") is True},
        "drift_webhook_stub_ok": {"passed": webhook.get("stub_ok") is True},
        "clinical_pending_human_gate": {
            "passed": clinical.get("gate_ok") is True
            and clinical.get("clinical_pending_status") in ("human_gate_pending", "ack_recorded"),
        },
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_p15_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_p15_status": "eval_path_locked_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "archive_rows": archive.get("archive_rows"),
        "clinical_pending_status": clinical.get("clinical_pending_status"),
        "reproduce": "py scripts/run_sasang_rail_p15_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "sasang_rail_p15_status": doc["sasang_rail_p15_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
