#!/usr/bin/env python3
"""Merge resume pack + shallow handoff + tier3 wire into LTM deep handoff envelope v1."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_cursor_deep_handoff_envelope_v1.schema.json"
DEFAULT_RESUME_JSON = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
DEFAULT_RESUME_MD = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
DEFAULT_HANDOFF = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
DEFAULT_TIER3_INDEX = (
    ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json"
)
DEFAULT_OUT_REPORTS = ROOT / "reports/mkm_cursor_deep_handoff_envelope_v1_latest.json"
DEFAULT_OUT_ARTIFACTS = (
    ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json"
)

LTM_DEEP_FETCH_BY_LANE: dict[str, list[str]] = {
    "infra": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_long_term_memory_graph_v1.json",
        "docs/final/MKM_OPS_MEMORY_AI_TO_AI_DEV_ONE_PAGER_V1.md",
    ],
    "oracle": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_long_term_memory_graph_v1.json",
        "docs/final/artifacts/mkm_ltm_inject_contract_v1.json",
    ],
    "ms": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_ops_memory_index_v1.json",
        "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
    ],
    "design": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_ops_memory_index_v1.json",
    ],
    "web_ops": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "docs/final/artifacts/global_payment_status_v1_latest.json",
    ],
    "ops": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_long_term_memory_graph_v1.json",
    ],
    "prophecy": [
        "reports/mkm_meta_cognition_shallow_deep_roadmap_v1_latest.json",
        "storage/meta/mkm_long_term_memory_graph_v1.json",
    ],
}

sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cursor_continuity_ssot_v1 import (  # noqa: E402
    merge_deep_fetch_queue,
    missing_required_paths,
    required_ssot_refs_payload,
)
from mkm_cursor_self_audit_lib_v1 import (  # noqa: E402
    build_agent_self_check,
    lane_default_topic_query,
)
from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    load_graph,
    route_concepts_by_query,
)

LOGOS_BIBLE_DENY_FRAGMENTS = (
    "graph_slice",
    "logos_studio/graph",
    "insight_bundle",
    "semantic_rag_bridge",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def load_schema(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_SCHEMA
    return json.loads(p.read_text(encoding="utf-8"))


def validate_jsonschema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def _is_denied_pillar_a_path(path: str) -> bool:
    low = path.lower().replace("\\", "/")
    return any(frag in low for frag in LOGOS_BIBLE_DENY_FRAGMENTS)


def _filter_handoff_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if p and not _is_denied_pillar_a_path(p)]


def _dedupe_paths(paths: list[str], *, limit: int = 12) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        norm = p.replace("\\", "/")
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= limit:
            break
    return out


def resolve_tier3_brief(lane: str, index_doc: dict[str, Any]) -> tuple[str, bool]:
    lanes = index_doc.get("lanes") if isinstance(index_doc.get("lanes"), dict) else {}
    entry = lanes.get(lane) if isinstance(lanes.get(lane), dict) else {}
    brief = str(entry.get("brief_artifact") or "").strip()
    pilot_ok = bool(entry.get("pilot_ok"))
    if not brief:
        brief = f"docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
    return brief, pilot_ok


def infer_lane(resume_pack: dict[str, Any], explicit: str) -> str:
    if explicit:
        return explicit
    opts = resume_pack.get("ops_memory_options") if isinstance(resume_pack.get("ops_memory_options"), dict) else {}
    lane = str(opts.get("lane") or "").strip()
    return lane or "infra"


def extract_pins(resume_pack: dict[str, Any]) -> list[dict[str, Any]]:
    pins_raw = resume_pack.get("ops_memory_pins")
    if not isinstance(pins_raw, list):
        return []
    pins: list[dict[str, Any]] = []
    for item in pins_raw[:6]:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or "").strip()
        if not node_id:
            continue
        pin: dict[str, Any] = {"node_id": node_id}
        if item.get("essence"):
            pin["essence"] = str(item["essence"])[:400]
        tags = item.get("must_keep_tags")
        if isinstance(tags, list):
            pin["must_keep_tags"] = [str(t) for t in tags[:8]]
        pins.append(pin)
    return pins


def _dedupe_strings(items: list[str], *, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def infer_ltm_concept_ids(
    handoff: dict[str, Any],
    lane: str,
    graph: dict[str, Any] | None = None,
) -> list[str]:
    concepts: list[str] = []
    hint = handoff.get("lens_route_hint") if isinstance(handoff.get("lens_route_hint"), dict) else {}
    lens_id = str(hint.get("lens_id") or lane).strip()
    if lens_id:
        concepts.append(f"lens_{lens_id}")
    concepts.append("ltm_graph_meta")
    anchors = handoff.get("anchor_ids") if isinstance(handoff.get("anchor_ids"), list) else []
    for a in anchors[:3]:
        concepts.append(str(a))
    if graph and graph.get("schema") == "mkm_long_term_memory_graph_v1":
        query = lane_default_topic_query(lane)
        for cid, _concept in route_concepts_by_query(graph, query, max_concepts=3):
            if cid not in concepts:
                concepts.append(cid)
    return _dedupe_strings(concepts, limit=5)


def build_envelope(
    *,
    lane: str,
    resume_pack: dict[str, Any],
    handoff: dict[str, Any],
    tier3_index: dict[str, Any],
    continuity_id: str = "",
    turn_meta_path: str = "",
    resume_json_path: Path = DEFAULT_RESUME_JSON,
    resume_md_path: Path = DEFAULT_RESUME_MD,
    handoff_path: Path = DEFAULT_HANDOFF,
) -> dict[str, Any]:
    if not continuity_id:
        continuity_id = f"pillar-a-{lane}-{_utc_now()[:10]}"
    graph: dict[str, Any] = {}
    try:
        graph = load_graph()
    except (OSError, json.JSONDecodeError, ValueError):
        graph = {}
    pins = extract_pins(resume_pack)
    if not pins:
        raise ValueError("resume pack has no ops_memory_pins")

    brief_path, pilot_ok = resolve_tier3_brief(lane, tier3_index)
    handoff_fetch = handoff.get("deep_fetch_next") if isinstance(handoff.get("deep_fetch_next"), list) else []
    handoff_fetch = [str(x) for x in handoff_fetch]

    deep_fetch_next = _dedupe_paths(
        [brief_path]
        + LTM_DEEP_FETCH_BY_LANE.get(lane, LTM_DEEP_FETCH_BY_LANE["infra"])
        + _filter_handoff_paths(handoff_fetch)
    )
    deep_fetch_next = merge_deep_fetch_queue(None, deep_fetch_next)
    still_missing = missing_required_paths(deep_fetch_next)
    if still_missing:
        deep_fetch_next = merge_deep_fetch_queue(deep_fetch_next, still_missing)

    if not deep_fetch_next:
        raise ValueError("deep_fetch_next empty after Pillar A filter")

    for p in deep_fetch_next:
        if _is_denied_pillar_a_path(p):
            raise ValueError(f"Pillar A envelope denied path: {p}")

    md_rel = _rel(resume_md_path)
    json_rel = _rel(resume_json_path)
    read_order = [
        md_rel,
        "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json",
        "MISSION_LOG.md",
        "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        *deep_fetch_next[:3],
    ]

    repro = (
        f"py scripts/build_mkm_cursor_deep_handoff_envelope_v1.py --lane {lane} "
        f"--continuity-id {continuity_id}"
    )

    envelope: dict[str, Any] = {
        "schema": "mkm_cursor_deep_handoff_envelope_v1",
        "generated_at_utc": _utc_now(),
        "lane": lane,
        "graph_axis": "A_ltm",
        "research_only": True,
        "send_gate": "HOLD",
        "continuity_id": continuity_id,
        "bench_ref": "MKM-BENCH-2026-003",
        "resume_pack": {
            "md_path": md_rel,
            "json_path": json_rel,
            "pins": pins,
        },
        "shallow_handoff": {
            "schema": str(handoff.get("schema") or "ollama_shallow_router_handoff_v1"),
            "source_path": _rel(handoff_path),
            "lens_route_hint": handoff.get("lens_route_hint"),
            "anchor_ids": handoff.get("anchor_ids") or [],
        },
        "tier3_wire": {
            "index_path": _rel(DEFAULT_TIER3_INDEX),
            "brief_path": brief_path,
            "pilot_ok": pilot_ok,
        },
        "ltm_concept_ids": infer_ltm_concept_ids(handoff, lane, graph),
        "deep_fetch_next": deep_fetch_next,
        "read_order": read_order,
        "required_ssot_refs": required_ssot_refs_payload(),
        "agent_self_check": build_agent_self_check(lane=lane, continuity_id=continuity_id),
        "ltm_topic_query": lane_default_topic_query(lane),
        "reproducible_command": repro,
    }
    if turn_meta_path:
        envelope["turn_meta_ref"] = {
            "schema": "mkm_cursor_turn_meta_v1",
            "path": turn_meta_path,
        }
    return envelope


def _coherence_rules(instance: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if instance.get("graph_axis") != "A_ltm":
        errs.append("graph_axis must be A_ltm for this builder.")
    for p in instance.get("deep_fetch_next") or []:
        if _is_denied_pillar_a_path(str(p)):
            errs.append(f"denied Pillar B path in deep_fetch_next: {p}")
    missing = missing_required_paths(list(instance.get("deep_fetch_next") or []))
    if missing:
        errs.append(f"required_ssot_missing in deep_fetch_next: {missing}")
    return errs


def validate_envelope(
    instance: dict[str, Any], *, schema_path: Path | None = None
) -> list[str]:
    errs: list[str] = []
    try:
        schema = load_schema(schema_path)
        validate_jsonschema(instance, schema)
    except Exception as exc:
        errs.append(f"jsonschema: {exc}")
    errs.extend(_coherence_rules(instance))
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="")
    parser.add_argument("--continuity-id", default="")
    parser.add_argument("--resume-json", type=Path, default=DEFAULT_RESUME_JSON)
    parser.add_argument("--resume-md", type=Path, default=DEFAULT_RESUME_MD)
    parser.add_argument("--handoff-json", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--tier3-index", type=Path, default=DEFAULT_TIER3_INDEX)
    parser.add_argument("--turn-meta", type=Path, default=None)
    parser.add_argument("--out-reports", type=Path, default=DEFAULT_OUT_REPORTS)
    parser.add_argument("--out-artifacts", type=Path, default=DEFAULT_OUT_ARTIFACTS)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--skip-artifacts-copy", action="store_true")
    args = parser.parse_args()

    resume_pack = _read_json(args.resume_json)
    handoff = _read_json(args.handoff_json) if args.handoff_json.is_file() else {
        "schema": "ollama_shallow_router_handoff_v1",
        "deep_fetch_next": [],
        "lens_route_hint": {"lens_id": args.lane or "infra"},
        "anchor_ids": [],
    }
    tier3_index = _read_json(args.tier3_index)
    lane = infer_lane(resume_pack, args.lane)
    turn_meta_path = _rel(args.turn_meta) if args.turn_meta and args.turn_meta.is_file() else ""

    doc = build_envelope(
        lane=lane,
        resume_pack=resume_pack,
        handoff=handoff,
        tier3_index=tier3_index,
        continuity_id=args.continuity_id,
        turn_meta_path=turn_meta_path,
        resume_json_path=args.resume_json,
        resume_md_path=args.resume_md,
        handoff_path=args.handoff_json,
    )
    errs = validate_envelope(doc, schema_path=args.schema)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    args.out_reports.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    args.out_reports.write_text(payload, encoding="utf-8")
    if not args.skip_artifacts_copy:
        args.out_artifacts.parent.mkdir(parents=True, exist_ok=True)
        args.out_artifacts.write_text(payload, encoding="utf-8")

    print(f"WROTE: {args.out_reports}")
    if not args.skip_artifacts_copy:
        print(f"WROTE: {args.out_artifacts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
