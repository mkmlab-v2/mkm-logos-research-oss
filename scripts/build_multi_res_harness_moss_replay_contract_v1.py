#!/usr/bin/env python3
"""Build Harness-1 / MOSS-inspired evidence→replay contract ([HYPO] B-track only).

Does NOT enable self-modify or todo_queue enqueue.

  py scripts/build_multi_res_harness_moss_replay_contract_v1.py
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODO_INDEX = ROOT / "reports/multi_res_todo_index_v1_latest.json"
APPROVAL_MAP = ROOT / "reports/delegation_multi_res_index_approval_map_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/multi_res_harness_moss_replay_contract_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    todo_meta = {}
    if TODO_INDEX.is_file():
        todo = json.loads(TODO_INDEX.read_text(encoding="utf-8-sig"))
        todo_meta = todo.get("meta") or {}

    global_stops: list[str] = []
    if APPROVAL_MAP.is_file():
        doc = json.loads(APPROVAL_MAP.read_text(encoding="utf-8-sig"))
        global_stops = list(doc.get("global_stop_rules") or [])

    doc = {
        "schema": "multi_res_harness_moss_replay_contract_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] pedagogical contract — Harness-1 state offload + MOSS replay shape; "
            "not production self-rewrite; todo_queue auto-enqueue forbidden"
        ),
        "todo_queue_auto_enqueue": False,
        "academic_refs": {
            "harness_1": "arXiv:2606.02373 — state-externalizing search harness",
            "moss": "arXiv:2605.22794 — source-level rewrite with human consent + rollback",
            "adacom": "arXiv:2605.30785 — external context manager, frozen agent",
        },
        "mkm_mapping": {
            "harness_working_memory": [
                "storage/meta/mkm_ops_memory_index_v1.json",
                "reports/multi_res_todo_index_v1_latest.json",
                "MISSION_LOG.md anchors",
            ],
            "policy_semantic_decisions": [
                "Cursor agent lane work",
                "build_mkm_chat_resume_pack_v1.py --lane",
            ],
            "moss_evidence_sources": [
                "reports/agent_decisions_log.jsonl",
                "reports/delegation_*_approval_map_v1_latest.json pending nodes",
                "pytest exit code",
                "scripts/check_mkm_ops_memory_must_keep_gate_v1.py",
            ],
        },
        "replay_pipeline": [
            {
                "step": 1,
                "name": "curate_failure_evidence",
                "owner": "harness",
                "scripts": ["reports/agent_decisions_log.jsonl tail", "delegation map pending"],
            },
            {
                "step": 2,
                "name": "candidate_change",
                "owner": "agent_review",
                "allowed": ["scripts/*.py", "tests/*.py", "reports/*_latest.json"],
                "forbidden": global_stops,
            },
            {
                "step": 3,
                "name": "ephemeral_replay",
                "owner": "sentinel",
                "gates": [
                    "py -m pytest tests/test_build_multi_res_todo_index_v1.py -q",
                    "py scripts/build_multi_res_todo_index_v1.py",
                    "py scripts/check_mkm_ops_memory_must_keep_gate_v1.py --phase source",
                ],
            },
            {
                "step": 4,
                "name": "promotion",
                "owner": "human",
                "requires": ["exit 0 on all replay gates", "no would_change_active", "no apply-active"],
                "rollback": "git restore / delegation map status revert",
            },
        ],
        "global_stop_rules": global_stops,
        "todo_index_snapshot": {
            "path": "reports/multi_res_todo_index_v1_latest.json",
            "n_low_res": todo_meta.get("n_low_res"),
            "n_mid_res": todo_meta.get("n_mid_res"),
            "n_high_res": todo_meta.get("n_high_res"),
        },
        "quality_claim_allowed": False,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
