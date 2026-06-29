#!/usr/bin/env python3
"""Gate: commander clinical de-identified row ingested with human-gate ack [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAINLINE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ACK = ROOT / "docs/final/artifacts/commander_attested_clinical_human_gate_ack_v1.json"
OUT = ROOT / "docs/final/artifacts/sasang_commander_clinical_ingest_gate_v1_latest.json"
DEID_ID = "commander_attested_clinical_deid_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mainline_row(pid: str) -> dict[str, Any] | None:
    if not MAINLINE.is_file():
        return None
    for line in MAINLINE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("person_id") or "") == pid:
            return row
    return None


def build() -> dict[str, Any]:
    ack = json.loads(ACK.read_text(encoding="utf-8-sig")) if ACK.is_file() else {}
    row = _mainline_row(DEID_ID) or {}
    br = row.get("birth_resolution") if isinstance(row.get("birth_resolution"), dict) else {}
    human_ack = ack.get("human_gate_ack") is True
    ack_id = str(ack.get("clinical_person_id") or ack.get("stub_person_id") or "")

    checks = {
        "human_gate_ack_recorded": {"passed": human_ack and ack_id == DEID_ID},
        "clinical_in_mainline": {"passed": row.get("person_id") == DEID_ID},
        "birth_resolution_present": {"passed": bool(str(br.get("birth_instant_utc") or "").strip())},
        "saju_output_present": {"passed": isinstance(row.get("saju_engine_output_v1"), dict)},
        "send_gate_hold": {"passed": ack.get("send_gate") == "HOLD" or not ACK.is_file()},
        "track_a_bridge_forbidden": {"passed": ack.get("track_a_bridge") is False or not ACK.is_file()},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_commander_clinical_ingest_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "clinical_ingest_status": "ingested_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "clinical_person_id": DEID_ID,
        "reproduce": "py scripts/build_sasang_commander_clinical_ingest_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "clinical_ingest_status": doc["clinical_ingest_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
