#!/usr/bin/env python3
"""Assemble narrative knowledge map bundle v1 — thin pointer merge [HYPO].

Merges existing B-track pilots (philosophy RAG, GraphRAG router snapshot,
Logos concept bridge registry, PersonaDiary inbox validation) without new graph
ingest or prophecy score mutation.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_ID = "narrative_knowledge_map_bundle_v1"
VERSION = "1.0.0"
DEFAULT_OUT = ROOT / "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json"
REPORTS_OUT = ROOT / "reports/narrative_knowledge_map_bundle_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/narrative_knowledge_map_bundle_v1.schema.json"

DEFAULT_PHILOSOPHY = ROOT / "docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json"
DEFAULT_GRAPHRAG = ROOT / "docs/final/artifacts/graphrag_pilot_router_latest.json"
DEFAULT_LOGOS_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
DEFAULT_PERSONADIARY_VAL = ROOT / "reports/personadiary_btrack_export_inbox_validation_latest.json"
DEFAULT_SEMANTIC_BRIDGE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
DEFAULT_FORBIDDEN = ROOT / "docs/final/artifacts/schemas/philosophy_lane_rag_pilot_forbidden_substrings_v1.json"
DEFAULT_LANE_OPS = ROOT / "reports/prophecy_lens_lane_ops_board_v1_latest.json"
DEFAULT_SIDEBAR_SMOKE = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
DEFAULT_HUMAN_RUBRIC = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_human_rubric_v1_latest.json"

MAX_BLOCKS = 24


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _pointer(path: Path, *, status: str | None = None) -> dict[str, Any]:
    present = path.is_file()
    row: dict[str, Any] = {"path": _rel(path), "present": present}
    if status:
        row["status"] = status
    elif present:
        doc = _read_json(path)
        if doc.get("status"):
            row["status"] = str(doc.get("status"))
    return row


def _blocks_from_philosophy(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, block in enumerate(doc.get("blocks") or []):
        if not isinstance(block, dict) or len(out) >= MAX_BLOCKS:
            break
        summary = str(block.get("summary") or "").strip()
        if not summary:
            continue
        out.append(
            {
                "block_id": f"philosophy_{i:03d}",
                "source_rail": str(block.get("source_rail") or "philosophy_lane"),
                "hypothesis_tag": str(block.get("hypothesis_tag") or "[HYPO]"),
                "summary": summary[:2000],
                **(
                    {"detail": str(block.get("detail") or "")[:8000]}
                    if str(block.get("detail") or "").strip()
                    else {}
                ),
                **(
                    {"evidence_path": block.get("evidence_path")}
                    if block.get("evidence_path") is not None
                    else {}
                ),
            }
        )
    return out


def _graphrag_snapshot(doc: dict[str, Any]) -> dict[str, Any] | None:
    if not doc:
        return None
    seeds = doc.get("seed_node_ids") or []
    selected = doc.get("selected_nodes") or []
    gate = ((doc.get("fact_lock") or {}).get("gate_status")) or doc.get("gate_status")
    return {
        "observation_only": bool(doc.get("observation_only", True)),
        "question": str(doc.get("question") or "")[:500] or None,
        "seed_node_count": len(seeds) if isinstance(seeds, list) else 0,
        "selected_node_count": len(selected) if isinstance(selected, list) else 0,
        "gate_status": str(gate) if gate is not None else None,
    }


def build_bundle(
    *,
    philosophy_path: Path,
    graphrag_path: Path,
    logos_registry_path: Path,
    personadiary_val_path: Path,
    semantic_bridge_path: Path,
    forbidden_path: Path,
    lane_ops_path: Path,
    sidebar_smoke_path: Path,
    human_rubric_path: Path,
) -> dict[str, Any]:
    philosophy = _read_json(philosophy_path)
    graphrag = _read_json(graphrag_path)
    blocks = _blocks_from_philosophy(philosophy)

    required_present = all(
        p.is_file()
        for p in (
            philosophy_path,
            graphrag_path,
            logos_registry_path,
            forbidden_path,
        )
    )

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "lane_id": "narrative_knowledge_map",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "decision_authority": "human_only",
        "prophecy_vote": "none",
        "policy": {
            "non_gating": True,
            "opt_in_only": True,
            "forbidden_config": _rel(forbidden_path),
        },
        "upstream_pointers": {
            "philosophy_lane_rag_pilot": _pointer(philosophy_path, status=str(philosophy.get("status") or "")),
            "graphrag_pilot_router": _pointer(graphrag_path),
            "logos_concept_bridge_registry": _pointer(logos_registry_path),
            "personadiary_inbox_validation": _pointer(personadiary_val_path),
            "semantic_rag_bridge_insight_bundle": _pointer(semantic_bridge_path),
            "lane_ops_board": _pointer(lane_ops_path),
            "personadiary_logos_sidebar_smoke": _pointer(sidebar_smoke_path),
            "personadiary_logos_sidebar_human_rubric": _pointer(human_rubric_path),
        },
        "graphrag_snapshot": _graphrag_snapshot(graphrag),
        "narrative_blocks": blocks,
        "consumer_contract_ko": (
            "본 번들은 PersonaDiary·내부 연구용 서사·개념 관계망 포인터입니다. "
            "prophecy lens vote·Primary score·Track A·실매매 sizing·send_gate 자동 승격에 "
            "합류하지 않습니다. 상징·은유 연결은 영감·브레인스토밍 참고만이며 인과 예측이 아닙니다."
        ),
        "ok": required_present and len(blocks) > 0,
        "headline_ko": [
            f"narrative_blocks={len(blocks)}",
            f"graphrag_observation_only={((graphrag or {}).get('observation_only'))}",
            "prophecy_vote=none",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--philosophy", type=Path, default=DEFAULT_PHILOSOPHY)
    ap.add_argument("--graphrag", type=Path, default=DEFAULT_GRAPHRAG)
    ap.add_argument("--logos-registry", type=Path, default=DEFAULT_LOGOS_REGISTRY)
    ap.add_argument("--personadiary-validation", type=Path, default=DEFAULT_PERSONADIARY_VAL)
    ap.add_argument("--semantic-bridge", type=Path, default=DEFAULT_SEMANTIC_BRIDGE)
    ap.add_argument("--forbidden-config", type=Path, default=DEFAULT_FORBIDDEN)
    ap.add_argument("--lane-ops", type=Path, default=DEFAULT_LANE_OPS)
    ap.add_argument("--sidebar-smoke", type=Path, default=DEFAULT_SIDEBAR_SMOKE)
    ap.add_argument("--human-rubric", type=Path, default=DEFAULT_HUMAN_RUBRIC)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reports-output", type=Path, default=REPORTS_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if ok=false")
    args = ap.parse_args(argv)

    payload = build_bundle(
        philosophy_path=args.philosophy,
        graphrag_path=args.graphrag,
        logos_registry_path=args.logos_registry,
        personadiary_val_path=args.personadiary_validation,
        semantic_bridge_path=args.semantic_bridge,
        forbidden_path=args.forbidden_config,
        lane_ops_path=args.lane_ops,
        sidebar_smoke_path=args.sidebar_smoke,
        human_rubric_path=args.human_rubric,
    )

    for path in (args.output, args.reports_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.strict and not payload.get("ok"):
        print("FAIL: narrative_knowledge_map_bundle not ok", file=sys.stderr)
        return 1
    print(
        f"OK blocks={len(payload.get('narrative_blocks') or [])} "
        f"ok={payload.get('ok')} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
