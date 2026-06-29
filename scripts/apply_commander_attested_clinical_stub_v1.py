#!/usr/bin/env python3
"""Apply commander clinical de-identified row via ingest — requires human-gate ack [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
PENDING = ROOT / "data/myeongni/curated_commander_clinical_pending_v1.jsonl"
MAINLINE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ACK = ROOT / "docs/final/artifacts/commander_attested_clinical_human_gate_ack_v1.json"
DEID_ID = "commander_attested_clinical_deid_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _in_mainline(pid: str) -> bool:
    if not MAINLINE.is_file():
        return False
    for line in MAINLINE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if str(json.loads(line).get("person_id") or "") == pid:
            return True
    return False


def apply(*, human_gate_ack: bool) -> dict[str, Any]:
    if not human_gate_ack:
        return {
            "schema": "commander_attested_clinical_apply_v1",
            "applied": False,
            "reason": "human_gate_ack_required",
            "reproduce": "py scripts/apply_commander_attested_clinical_stub_v1.py --human-gate-ack",
        }

    if _in_mainline(DEID_ID):
        ack_doc = {
            "schema": "commander_attested_clinical_human_gate_ack_v1",
            "generated_at_utc": _utc(),
            "human_gate_ack": True,
            "clinical_person_id": DEID_ID,
            "applied_to_mainline": False,
            "already_present": True,
            "lane": "track_b_hypo",
            "send_gate": "HOLD",
            "track_a_bridge": False,
        }
        ACK.parent.mkdir(parents=True, exist_ok=True)
        ACK.write_text(json.dumps(ack_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "schema": "commander_attested_clinical_apply_v1",
            "applied": False,
            "already_present": True,
            "clinical_person_id": DEID_ID,
            "ack_path": str(ACK).replace("\\", "/"),
        }

    proc = subprocess.run(
        [
            PY,
            str(ROOT / "scripts/ingest_curated_saju_joint_v1.py"),
            "--input-jsonl",
            str(PENDING),
            "--target-jsonl",
            str(MAINLINE),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    ingest_summary: dict[str, Any] = {}
    try:
        ingest_summary = json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        ingest_summary = {"parse_error": True, "stdout_tail": (proc.stdout or "")[-300:]}

    applied = proc.returncode == 0 and int(ingest_summary.get("appended") or 0) >= 1
    ack_doc = {
        "schema": "commander_attested_clinical_human_gate_ack_v1",
        "generated_at_utc": _utc(),
        "human_gate_ack": True,
        "clinical_person_id": DEID_ID,
        "applied_to_mainline": applied,
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "track_a_bridge": False,
        "ingest_summary": ingest_summary,
    }
    ACK.parent.mkdir(parents=True, exist_ok=True)
    ACK.write_text(json.dumps(ack_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema": "commander_attested_clinical_apply_v1",
        "applied": applied,
        "clinical_person_id": DEID_ID,
        "ingest_exit_code": proc.returncode,
        "ingest_summary": ingest_summary,
        "ack_path": str(ACK).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--human-gate-ack", action="store_true")
    args = ap.parse_args()
    doc = apply(human_gate_ack=args.human_gate_ack)
    print(json.dumps(doc, ensure_ascii=False))
    if doc.get("reason") == "human_gate_ack_required":
        return 2
    return 0 if doc.get("applied") or doc.get("already_present") else 1


if __name__ == "__main__":
    raise SystemExit(main())
