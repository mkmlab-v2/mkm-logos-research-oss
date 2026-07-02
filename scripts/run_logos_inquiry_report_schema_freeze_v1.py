#!/usr/bin/env python3
"""Freeze logos inquiry report v1 schema + sample + query contract spec (P0-1a)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_report_v1 import (  # noqa: E402
    SCHEMA,
    build_inquiry_report,
    load_freeze_lexicon_meta,
    load_sasang_regime_hint_b_track,
)
from check_logos_research_text_mvp_intake_v1 import evaluate_intake  # noqa: E402

OUT_FREEZE = ROOT / "reports/logos_inquiry_report_schema_freeze_v1_latest.json"
OUT_SPEC = ROOT / "docs/final/artifacts/logos_inquiry_query_contract_v1_latest.json"
OUT_SAMPLE = ROOT / "reports/logos_inquiry_report_sample_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_inquiry_report_v1.schema.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sample_payload() -> dict[str, Any]:
    return {
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "preset_id": "job_job_suffering_reason",
        "answer": "[HYPO] 욥기 고난·의·회복 서사 — 학파별 puzzle vs pastoral.",
        "path": {
            "steps": ["lemma_suffering", "Job.1.21", "Job.42.10"],
            "verse_refs": ["Job.1.21", "Job.42.10"],
            "node_ids": ["lemma_suffering"],
        },
        "conflict_context": {
            "groups": [
                {
                    "conflict_group_id": "job_suffering",
                    "lexicon_base": "suffering",
                    "school_count": 2,
                    "schools": [
                        {
                            "school_tier": "historical_grammatical",
                            "interpretation_ko": "theodicy puzzle",
                            "citation_lock_anchors": ["Job.1.21"],
                        },
                        {
                            "school_tier": "pastoral",
                            "interpretation_ko": "comfort narrative",
                            "citation_lock_anchors": ["Job.42.10"],
                        },
                    ],
                }
            ]
        },
    }


def build_contract_spec(*, root: Path = ROOT) -> dict[str, Any]:
    return {
        "schema": "logos_inquiry_query_contract_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "continuity_id": "logos-oss-export-ci-2026-06-30",
        "phase": "P0-security-wire",
        "endpoint": {
            "method": "POST",
            "path": "/api/logos-research/query",
            "unified": True,
            "deprecated_alias": "/api/logos-research/qa",
        },
        "request": {
            "query": "string (required for dynamic match)",
            "preset_id": "optional string",
            "output_format": "studio_v1 | inquiry_report_v1 (default studio_v1)",
            "domain_lane": "logos | life | observe (inquiry only)",
            "intent_chip": "reports | observe | … (inquiry only)",
            "embed_demo": "boolean (studio only)",
            "ecs_expand_poc": "boolean (studio only)",
        },
        "response_inquiry": {
            "ok": True,
            "api_contract": "logos_inquiry_query_v1",
            "output_format": "inquiry_report_v1",
            "tier": "standard",
            "report_schema": SCHEMA,
            "report": "logos_inquiry_report_v1 object",
        },
        "response_studio_default": {
            "api_contract": "logos_studio_v2_dynamic_rag_query_v1",
            "result": "logos_research_studio_query_v1",
        },
        "streaming": {"status": "active", "slot": "P0-1b", "contract": "logos_inquiry_stream_v1"},
        "security_wire": {
            "s2_freeze_manifest_runtime": True,
            "s3_sasang_regime_hint_b_track": True,
            "s4_allowlist": "docs/final/artifacts/logos_inquiry_s4_synthesis_allowlist_v1_latest.json",
            "inquiry_synthesis_llm_default": "off",
        },
        "report_schema_path": str(SCHEMA_PATH.relative_to(root)).replace("\\", "/"),
        "reproduce": "py scripts/run_logos_inquiry_report_schema_freeze_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sample_q = "욥기 — 고난과 의의, 학파별 해석 차이는?"
    intake = evaluate_intake(question=sample_q, domain_lane="logos", intent_chip="reports")
    intake_summary = {
        "intake_gate": intake["intake_gate"],
        "domain_lane": intake["input"]["domain_lane"],
        "intent_chip": intake["input"]["intent_chip"],
        "failed_checks": intake.get("failed_checks") or [],
        "reverse_questions_ko": intake.get("reverse_questions_ko") or [],
    }
    freeze_meta = load_freeze_lexicon_meta(root=args.root)
    sasang_hint = load_sasang_regime_hint_b_track(root=args.root)
    sample_report = build_inquiry_report(
        _sample_payload(),
        query=sample_q,
        intake=intake_summary,
        freeze_meta=freeze_meta,
        chain_exit_code=0,
        sasang_hint=sasang_hint,
    )
    contract = build_contract_spec(root=args.root)

    freeze_doc = {
        "schema": "logos_inquiry_report_schema_freeze_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "phase": "P0-1a",
        "chain_exit_code": 0,
        "report_schema": SCHEMA,
        "report_schema_path": str(SCHEMA_PATH.relative_to(args.root)).replace("\\", "/"),
        "contract_spec_path": str(OUT_SPEC.relative_to(args.root)).replace("\\", "/"),
        "sample_report_path": str(OUT_SAMPLE.relative_to(args.root)).replace("\\", "/"),
        "freeze_lexicon_meta": freeze_meta,
        "reproduce": "py scripts/run_logos_inquiry_report_schema_freeze_v1.py",
    }

    if args.dry_run:
        print(json.dumps({"contract": contract, "sample_sections": list(sample_report["sections"].keys())}, ensure_ascii=False, indent=2))
        return 0

    OUT_FREEZE.parent.mkdir(parents=True, exist_ok=True)
    OUT_SPEC.parent.mkdir(parents=True, exist_ok=True)
    OUT_FREEZE.write_text(json.dumps(freeze_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_SPEC.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_SAMPLE.write_text(json.dumps(sample_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "freeze": str(OUT_FREEZE), "contract": str(OUT_SPEC), "sample": str(OUT_SAMPLE)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
