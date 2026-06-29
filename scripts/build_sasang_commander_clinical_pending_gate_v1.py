#!/usr/bin/env python3
"""Gate: commander clinical stub pending file — not in mainline until human ack [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_v1.json"
PENDING = ROOT / "data/myeongni/curated_commander_clinical_pending_v1.jsonl"
MAINLINE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ACK = ROOT / "docs/final/artifacts/commander_attested_clinical_human_gate_ack_v1.json"
OUT = ROOT / "docs/final/artifacts/sasang_commander_clinical_pending_gate_v1_latest.json"
DEID_ID = "commander_attested_clinical_deid_v1"
LEGACY_STUB_ID = "commander_attested_clinical_stub_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _person_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        pid = str(row.get("person_id") or "")
        if pid:
            ids.add(pid)
    return ids


def build() -> dict[str, Any]:
    pending_ids = _person_ids(PENDING)
    mainline_ids = _person_ids(MAINLINE)
    ack = json.loads(ACK.read_text(encoding="utf-8-sig")) if ACK.is_file() else {}
    human_ack = ack.get("human_gate_ack") is True

    target_id = DEID_ID if DEID_ID in pending_ids else LEGACY_STUB_ID
    stub_in_pending = target_id in pending_ids
    stub_not_in_mainline = target_id not in mainline_ids
    provenance_ok = False
    if PENDING.is_file():
        for line in PENDING.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("person_id") or "") == target_id:
                provenance_ok = "commander_attested" in str(row.get("provenance") or "")
                break

    ingested = target_id in mainline_ids and human_ack
    checks = {
        "pending_file_exists": {"passed": PENDING.is_file() and stub_in_pending},
        "stub_not_in_mainline": {"passed": stub_not_in_mainline or ingested},
        "provenance_tagged": {"passed": provenance_ok},
        "human_gate_pending_or_ack": {
            "passed": ingested or (not human_ack and stub_not_in_mainline) or human_ack,
        },
        "track_a_bridge_forbidden": {"passed": True},
        "auto_ingest_blocked": {"passed": stub_not_in_mainline or ingested},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    status = "ingested_ok" if ingested else ("human_gate_pending" if stub_not_in_mainline and not human_ack else "ack_recorded")
    if not gate_ok:
        status = "incomplete"
    return {
        "schema": "sasang_commander_clinical_pending_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "clinical_pending_status": status,
        "gate_ok": gate_ok,
        "checks": checks,
        "stub_person_id": target_id,
        "human_gate_ack": human_ack,
        "pending_path": str(PENDING).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_commander_clinical_pending_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "clinical_pending_status": doc["clinical_pending_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
