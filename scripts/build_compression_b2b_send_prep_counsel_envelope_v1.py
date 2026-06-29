#!/usr/bin/env python3
"""Compression B2B SEND-prep counsel envelope metadata [HOLD until counsel_signoff]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/compression_b2b_send_prep_counsel_envelope_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/compression_proof_project_closure_v1_latest.json"
SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
INTAKE = ROOT / "docs/final/artifacts/compression_pilot_target_intake_kit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    closure = _load(CLOSURE)
    signoff = _load(SIGNOFF)
    return {
        "schema": "compression_b2b_send_prep_counsel_envelope_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": signoff.get("send_gate") or "HOLD",
        "ready_for_external_send": bool(signoff.get("ready_for_external_send")),
        "envelope_status": "send_prep_counsel_review",
        "agent_automation_complete": closure.get("agent_automation_complete"),
        "proof_sprint_level": closure.get("proof_sprint_level"),
        "commander_signoff": bool(signoff.get("commander_signoff")),
        "counsel_signoff": bool(signoff.get("counsel_signoff")),
        "human_gated_remainder": closure.get("human_gated_remainder"),
        "intake_kit": INTAKE.relative_to(ROOT).as_posix(),
        "manifest_builder": "scripts/build_compression_b2b_counsel_export_manifest_v1.py",
        "zip_builder": "scripts/build_compression_b2b_counsel_zip_pack_v1.py",
        "scaffold_invoke": "scripts/Invoke-CompressionSendPrepScaffold_v1.ps1",
        "legal_send_unlock": (
            "py scripts/apply_compression_b2b_legal_send_signoff_v1.py "
            "--commander-acknowledge --counsel-acknowledge"
        ),
        "guardrail_ko": (
            "자동화 완료≠대외 SEND. 고객 마스킹 JSONL 실측 전 tenant stub %·Track A 47%·handoff 99% 헤드라인 금지."
        ),
        "guardrail_en": (
            "Automation complete does not authorize external SEND. "
            "No tenant stub %, Track A 47%, or handoff 99% headlines until customer-masked JSONL measured."
        ),
        "fail_comp_004": [
            "Do not merge open_long % with Track A % with handoff % in one headline",
            "Do not use tenant stub 97.6% as marketing proof",
            "repair_v2 uplift is operational evidence only — not raw model-core proof",
        ],
        "reproduce": [
            "powershell -File scripts/Invoke-CompressionSendPrepScaffold_v1.ps1 -BuildCounselEnvelope",
            "py scripts/build_compression_b2b_send_prep_counsel_envelope_v1.py",
            "py scripts/build_compression_b2b_counsel_export_manifest_v1.py --fail-if-missing",
            "py scripts/build_compression_b2b_counsel_zip_pack_v1.py",
        ],
    }


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "send_gate": doc["send_gate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
