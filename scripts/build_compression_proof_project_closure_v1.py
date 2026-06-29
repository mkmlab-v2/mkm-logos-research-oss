#!/usr/bin/env python3
"""Proof project closure report — agent-complete vs human-gated remainder."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "reports/compression_evidence_lv1_chain_v1_latest.json"
REPRODUCE = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/compression_proof_project_closure_v1_latest.json"
INTAKE_TEMPLATE = ROOT / "docs/final/artifacts/compression_b2b_prospect_poc_corpus_intake_v1.template.json"
SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
PILOT_ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"
COMPLETION = ROOT / "reports/compression_proof_completion_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    chain = _load(CHAIN)
    pack = _load(REPRODUCE)
    pilot = (pack.get("skus") or {}).get("pilot_roi") or {}
    signoff = _load(SIGNOFF)
    pilot_doc = _load(PILOT_ROI)
    completion = _load(COMPLETION)
    agent_complete = bool(chain.get("chain_ok")) and pack.get("proof_sprint_level") == "lv3"
    return {
        "schema": "compression_proof_project_closure_v1",
        "generated_at_utc": _utc(),
        "proof_sprint_level": pack.get("proof_sprint_level"),
        "agent_automation_complete": agent_complete,
        "chain_ok": chain.get("chain_ok"),
        "send_gate": pack.get("send_gate", "HOLD"),
        "ready_for_external_send": bool(pack.get("ready_for_external_send")),
        "completed_automated": [
            "open_structured_corpus_128",
            "open_structured_long_48",
            "golden40_public_safe_40",
            "handoff_token_bench",
            "reproduce_pack_lv3",
            "evidence_index_lv2_mount",
            "media_fact_sheets_sync",
            "a_codeai_reproduce_bundle",
            "prospect_poc_intake_template",
            "pilot_roi_rehearsal_chain",
            "commander_signoff_recorded",
        ],
        "human_gated_remainder": [
            {
                "id": "pilot_roi_customer_dollar",
                "status": pilot_doc.get("status") or pilot.get("status"),
                "measured_proxy": pilot_doc.get("measured_proxy") or pilot.get("measured_proxy"),
                "intake_template": INTAKE_TEMPLATE.relative_to(ROOT).as_posix()
                if INTAKE_TEMPLATE.is_file()
                else None,
                "note": "Rehearsal measured; replace with customer-masked JSONL for dollar/KRW ROI.",
            },
            {
                "id": "legal_send_unlock",
                "status": signoff.get("send_gate", "HOLD"),
                "commander_signoff": signoff.get("commander_signoff"),
                "counsel_signoff": signoff.get("counsel_signoff"),
                "note": "External SEND needs counsel_signoff true (RQ-009); commander pre-approval recorded.",
            },
        ],
        "one_command_verify": "py scripts/run_compression_proof_completion_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--run-chain", action="store_true")
    args = ap.parse_args()
    if args.run_chain:
        proc = subprocess.run(
            [sys.executable, "scripts/run_compression_evidence_lv1_chain_v1.py"],
            cwd=str(ROOT),
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("agent_automation_complete"),
                "agent_automation_complete": doc.get("agent_automation_complete"),
                "output": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("agent_automation_complete") else 1


if __name__ == "__main__":
    raise SystemExit(main())
