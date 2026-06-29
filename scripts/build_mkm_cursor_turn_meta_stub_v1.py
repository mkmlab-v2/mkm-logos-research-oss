#!/usr/bin/env python3
"""Build mkm_cursor_turn_meta_v1 stub — Cursor LTM turn audit (Pillar A, BENCH-003)."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_cursor_turn_meta_v1.schema.json"
DEFAULT_OUT = ROOT / "reports/mkm_cursor_turn_meta_stub_v1_latest.json"
DEFAULT_RESUME = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.md"

LANE_NODE_IDS: dict[str, list[str]] = {
    "infra": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_infra",
    ],
    "oracle": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_oracle",
    ],
    "ms": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_ms",
    ],
    "design": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
    ],
    "web_ops": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
    ],
    "ops": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_infra",
    ],
    "prophecy": [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_oracle",
    ],
}

LANE_TOKEN_ESTIMATE: dict[str, int] = {
    "infra": 111,
    "oracle": 426,
    "ms": 117,
    "design": 202,
    "web_ops": 155,
    "ops": 111,
    "prophecy": 426,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_schema(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_SCHEMA
    return json.loads(p.read_text(encoding="utf-8"))


def validate_jsonschema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def coherence_rules(instance: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if len(instance.get("deep_reads") or []) > 3:
        errs.append("deep_reads exceeds max 3 per turn.")
    axis = instance.get("graph_axis")
    if axis == "B_logos_bible" and instance.get("lane") == "infra":
        errs.append("infra lane turn meta should use graph_axis=A_ltm (Logos UI = other chat).")
    for path in instance.get("deep_fetch_next") or []:
        low = path.lower()
        if "graph_slice" in low or "logos_studio/graph" in low:
            errs.append(f"deep_fetch_next must not reference Logos graph_slice in Pillar A: {path}")
    return errs


def validate_turn_meta(
    instance: dict[str, Any], *, schema_path: Path | None = None
) -> list[str]:
    try:
        schema = load_schema(schema_path)
        validate_jsonschema(instance, schema)
    except Exception as exc:
        return [f"jsonschema: {exc}"]
    return coherence_rules(instance)


def build_stub(
    *,
    lane: str = "infra",
    continuity_id: str = "",
    graph_axis: str = "A_ltm",
    turn_id: str = "",
    bench_ref: str = "MKM-BENCH-2026-003",
    deep_reads: list[dict[str, Any]] | None = None,
    deep_fetch_next: list[str] | None = None,
) -> dict[str, Any]:
    if lane not in LANE_NODE_IDS:
        raise ValueError(f"unsupported lane: {lane}")
    if not continuity_id:
        continuity_id = f"pillar-a-{lane}-{_utc_now()[:10]}"
    if not turn_id:
        turn_id = f"cursor-turn-{uuid.uuid4().hex[:12]}"
    node_ids = LANE_NODE_IDS[lane]
    token_est = LANE_TOKEN_ESTIMATE.get(lane, 143)
    resume_ref = "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
    if deep_reads is None:
        deep_reads = [
            {
                "path": "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
                "concept_id": "ltm_graph_meta",
                "status": "planned",
            }
        ]
    if deep_fetch_next is None:
        deep_fetch_next = [
            "docs/final/schemas/mkm_cursor_turn_meta_v1.schema.json",
            "storage/meta/mkm_long_term_memory_graph_v1.json",
        ]
    repro = (
        f"py scripts/build_mkm_cursor_turn_meta_stub_v1.py "
        f"--lane {lane} --continuity-id {continuity_id}"
    )
    return {
        "schema": "mkm_cursor_turn_meta_v1",
        "turn_id": turn_id,
        "generated_at_utc": _utc_now(),
        "continuity_id": continuity_id,
        "lane": lane,
        "graph_axis": graph_axis,
        "research_only": True,
        "send_gate": "HOLD",
        "bench_ref": bench_ref,
        "shallow_pins": {
            "node_ids": node_ids,
            "token_estimate": token_est,
            "resume_pack_ref": resume_ref,
        },
        "shallow_used": {
            "inject_mode": "essence_only",
            "node_ids_used": node_ids,
            "token_estimate": token_est,
        },
        "deep_reads": deep_reads,
        "deep_fetch_next": deep_fetch_next,
        "verify_status": "pending",
        "unverified_claims": [],
        "reproducible_command": repro,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="infra")
    parser.add_argument("--continuity-id", default="")
    parser.add_argument("--graph-axis", default="A_ltm", choices=["A_ltm", "B_logos_bible"])
    parser.add_argument("--turn-id", default="")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--validate-only", type=Path, default=None)
    args = parser.parse_args()

    if args.validate_only:
        doc = json.loads(args.validate_only.read_text(encoding="utf-8"))
        errs = validate_turn_meta(doc, schema_path=args.schema)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print(f"OK: {args.validate_only}")
        return 0

    doc = build_stub(
        lane=args.lane,
        continuity_id=args.continuity_id,
        graph_axis=args.graph_axis,
        turn_id=args.turn_id,
    )
    errs = validate_turn_meta(doc, schema_path=args.schema)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
