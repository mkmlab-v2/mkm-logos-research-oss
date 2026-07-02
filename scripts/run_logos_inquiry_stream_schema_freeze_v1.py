#!/usr/bin/env python3
"""Freeze logos inquiry stream v1 contract (P0-1b · SSE 2-phase)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_stream_v1 import (  # noqa: E402
    STREAM_SCHEMA,
    build_stream_sequence_from_payload,
)
from check_logos_research_text_mvp_intake_v1 import evaluate_intake  # noqa: E402

OUT_FREEZE = ROOT / "reports/logos_inquiry_stream_schema_freeze_v1_latest.json"
OUT_CONTRACT = ROOT / "docs/final/artifacts/logos_inquiry_stream_contract_v1_latest.json"
OUT_SAMPLE = ROOT / "reports/logos_inquiry_stream_sample_events_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_inquiry_stream_v1.schema.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sample_payload() -> dict[str, Any]:
    return {
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "answer": "첫 문장입니다. 둘째 문장은 조금 더 깁니다. 셋째로 마무리합니다.",
        "path": {"verse_refs": ["Job.1.21"], "steps": ["lemma_faith"], "node_ids": ["lemma_faith"]},
        "conflict_context": {"groups": []},
    }


def build_contract() -> dict[str, Any]:
    return {
        "schema": "logos_inquiry_stream_contract_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "phase": "P0-1b",
        "continuity_id": "logos-oss-export-ci-2026-06-30",
        "endpoint": {
            "method": "POST",
            "path": "/api/logos-research/query",
            "content_type": "text/event-stream",
            "conditions": {
                "output_format": "inquiry_report_v1",
                "stream_s4": True,
            },
        },
        "event_sequence": ["snapshot", "s4_delta", "s4_done", "done"],
        "phase_a": {
            "description": "S1 S2 S3 + S5 provisional in first snapshot event",
            "s5_signoff_status": "provisional",
            "s5_sha256": "null until done",
        },
        "phase_b": {
            "description": "S4 body_ko only via s4_delta chunks then s4_done",
            "chunk_chars_default": 48,
        },
        "final_seal": {
            "event": "done",
            "s5_signoff_status": "final",
            "sections_payload_sha256": "includes complete S4",
        },
        "stream_schema_path": str(SCHEMA_PATH.relative_to(ROOT)).replace("\\", "/"),
        "report_schema": "logos_inquiry_report_v1",
        "reproduce": "py scripts/run_logos_inquiry_stream_schema_freeze_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    q = "욥기 고난과 의 — 학파별 해석 차이는?"
    intake = evaluate_intake(question=q, domain_lane="logos")
    intake_summary = {
        "intake_gate": intake["intake_gate"],
        "domain_lane": intake["input"]["domain_lane"],
        "intent_chip": intake["input"]["intent_chip"],
    }
    events = build_stream_sequence_from_payload(
        _sample_payload(), query=q, intake=intake_summary, chunk_chars=24
    )
    contract = build_contract()
    freeze_doc = {
        "schema": "logos_inquiry_stream_schema_freeze_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "phase": "P0-1b",
        "chain_exit_code": 0,
        "stream_schema": STREAM_SCHEMA,
        "event_count": len(events),
        "event_types": [e["event"] for e in events],
        "contract_path": str(OUT_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "reproduce": "py scripts/run_logos_inquiry_stream_schema_freeze_v1.py",
    }

    if args.dry_run:
        print(json.dumps({"events": len(events), "types": freeze_doc["event_types"]}, ensure_ascii=False))
        return 0

    OUT_FREEZE.parent.mkdir(parents=True, exist_ok=True)
    OUT_CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    OUT_FREEZE.write_text(json.dumps(freeze_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_SAMPLE.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "freeze": str(OUT_FREEZE), "events": len(events)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
