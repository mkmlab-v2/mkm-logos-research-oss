#!/usr/bin/env python3
"""Assemble CDIM v1: read-only merge of independent lenses + typed cross-refs.

Does not inject ohaeng/yin-yang on Logos verse index. Does not recompute lens scores.
SSOT design: docs/final/LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FUSION = ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
DEFAULT_CROSS_RAG = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_fusion_latest.json"
DEFAULT_STATE_MAP = ROOT / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json"
DEFAULT_CONCEPT_BRIDGE = (
    ROOT / "docs" / "final" / "artifacts" / "logos_concept_bridge_semiconductor_poc_v1_latest.json"
)
DEFAULT_BRIDGE_REGISTRY = (
    ROOT / "docs" / "final" / "artifacts" / "logos_concept_bridge_registry_v1_latest.json"
)
DEFAULT_SUBGRAPH_ROUTER = (
    ROOT / "docs" / "final" / "artifacts" / "logos_subgraph_graphrag_router_v1_latest.json"
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_cross_domain_interface_latest.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "logos_cross_domain_interface_v1.schema.json"
DESIGN_DOC = "docs/final/LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md"

FORBIDDEN_CLAIMS = [
    "universal_ohaeng_taxonomy_on_bible_corpus",
    "logos_gating_live_trade",
    "ms_era_metrics_other_than_text_blind_4_3pct",
    "prophecy_hit_from_cdim_assembly",
]

CDIM_VERSION = "1.0.0"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _manifest_entry(path: Path) -> dict[str, Any]:
    return {"path": _rel_repo(path), "present": path.is_file()}


def _lens_domain(lens_id: str) -> str:
    lid = (lens_id or "").lower()
    if "myeongni" in lid or lid == "market_myeongni":
        return "myeongni"
    if "sasang" in lid or lid == "market_sasang":
        return "sasang"
    if "logos" in lid:
        return "logos"
    return "fusion"


def _cross_ref_fusion(fusion: dict[str, Any], rel_path: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    conflict_count = int(consensus.get("conflict_count") or 0)
    agreement = float(consensus.get("agreement_rate") or 0.0)
    rtype = "align" if conflict_count == 0 and agreement >= 0.66 else "conflict"
    refs.append(
        {
            "relation_type": rtype,
            "from_domain": "fusion",
            "to_domain": "cdim",
            "evidence_path": rel_path,
            "note": "verbatim from independent_lens_fusion_stub; no merged ontology",
        }
    )
    csum = fusion.get("conflict_summary") if isinstance(fusion.get("conflict_summary"), dict) else {}
    minority = csum.get("minority_lens_ids") if isinstance(csum.get("minority_lens_ids"), list) else []
    for mid in minority[:3]:
        refs.append(
            {
                "relation_type": "conflict",
                "from_domain": _lens_domain(str(mid)),
                "to_domain": "fusion",
                "evidence_path": rel_path,
                "note": "minority_lens in fusion_stub conflict_summary",
            }
        )
    logos_refs = csum.get("logos_evidence_verse_ids")
    if isinstance(logos_refs, list) and logos_refs:
        refs.append(
            {
                "relation_type": "ref_only",
                "from_domain": "logos",
                "to_domain": "fusion",
                "evidence_path": rel_path,
                "verse_ids": [str(v) for v in logos_refs[:20]],
                "note": "Logos evidence_refs only; no score injection into other lenses",
            }
        )
    return refs


def _cross_ref_state_mapping(doc: dict[str, Any], rel_path: str) -> dict[str, Any] | None:
    assignments = doc.get("assignments") or doc.get("mapping") or doc.get("pairs")
    if not isinstance(assignments, list) or not assignments:
        return None
    verse_ids: list[str] = []
    for row in assignments[:16]:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id") or row.get("logos_verse_id")
        if vid:
            verse_ids.append(str(vid))
    return {
        "relation_type": "4d_cosine_assign",
        "from_domain": "logos",
        "to_domain": "myeongni",
        "evidence_path": rel_path,
        "verse_ids": verse_ids[:16],
        "note": "join_logos_verses_myeongni_states_4d [HYPO]; not ohaeng verse labels",
    }


def _cross_ref_concept_bridge(doc: dict[str, Any], rel_path: str) -> dict[str, Any]:
    verse_ids: list[str] = []
    for node in doc.get("nodes") or []:
        if isinstance(node, dict) and node.get("kind") == "verse_ref":
            vid = node.get("verse_id")
            if vid:
                verse_ids.append(str(vid))
    for p in doc.get("paths") or []:
        if not isinstance(p, dict):
            continue
        for step in p.get("steps") or []:
            if isinstance(step, str) and step.startswith("verse:"):
                pass
    return {
        "relation_type": "concept_path",
        "from_domain": "logos",
        "to_domain": "cdim",
        "evidence_path": rel_path,
        "verse_ids": sorted(set(verse_ids))[:32],
        "note": "concept_bridge semantic path demo; no prophecy claim",
    }


def _cross_ref_cross_rag(rel_path: str) -> dict[str, Any]:
    return {
        "relation_type": "ref_only",
        "from_domain": "fusion",
        "to_domain": "cdim",
        "evidence_path": rel_path,
        "note": "cross_lens_rag_fusion dashboard snapshot; observation only",
    }


def _cross_ref_subgraph_router(doc: dict[str, Any], rel_path: str) -> dict[str, Any]:
    verse_ids: list[str] = []
    for route in doc.get("routes") or []:
        if not isinstance(route, dict):
            continue
        for vid in route.get("verse_ids") or []:
            verse_ids.append(str(vid))
    return {
        "relation_type": "graphrag_route",
        "from_domain": "logos",
        "to_domain": "cdim",
        "evidence_path": rel_path,
        "verse_ids": sorted(set(verse_ids))[:32],
        "note": "subgraph GraphRAG router demo; no prophecy claim",
    }


def _append_bridge_registry_refs(
    *,
    registry_path: Path,
    cross_refs: list[dict[str, Any]],
    inputs_manifest: dict[str, Any],
) -> None:
    if not registry_path.is_file():
        return
    reg = _read_json(registry_path)
    if not reg:
        return
    inputs_manifest["concept_bridge_registry"] = _manifest_entry(registry_path)
    for entry in reg.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        cb_path = ROOT / rel
        if not cb_path.is_file():
            continue
        cb = _read_json(cb_path)
        if cb and cb.get("schema") == "logos_concept_bridge_v1":
            cross_refs.append(_cross_ref_concept_bridge(cb, rel))


def assemble(
    *,
    fusion_path: Path,
    cross_rag_path: Path | None,
    state_map_path: Path | None,
    concept_bridge_path: Path | None,
    bridge_registry_path: Path | None,
    subgraph_router_path: Path | None,
    field_regime_id: str,
) -> dict[str, Any]:
    fusion = _read_json(fusion_path)
    if not fusion or fusion.get("schema") != "independent_lens_fusion_stub_v0":
        raise SystemExit(f"missing or invalid fusion stub: {fusion_path}")

    inputs_manifest: dict[str, Any] = {
        "fusion_stub": _manifest_entry(fusion_path),
    }
    cross_refs: list[dict[str, Any]] = _cross_ref_fusion(fusion, _rel_repo(fusion_path))

    if cross_rag_path:
        inputs_manifest["cross_lens_rag"] = _manifest_entry(cross_rag_path)
        if cross_rag_path.is_file():
            cross_refs.append(_cross_ref_cross_rag(_rel_repo(cross_rag_path)))

    if state_map_path:
        inputs_manifest["logos_state_mapping"] = _manifest_entry(state_map_path)
        sm = _read_json(state_map_path)
        if sm:
            ref = _cross_ref_state_mapping(sm, _rel_repo(state_map_path))
            if ref:
                cross_refs.append(ref)

    if bridge_registry_path and bridge_registry_path.is_file():
        _append_bridge_registry_refs(
            registry_path=bridge_registry_path,
            cross_refs=cross_refs,
            inputs_manifest=inputs_manifest,
        )
    elif concept_bridge_path:
        inputs_manifest["concept_bridge"] = _manifest_entry(concept_bridge_path)
        cb = _read_json(concept_bridge_path)
        if cb and cb.get("schema") == "logos_concept_bridge_v1":
            cross_refs.append(_cross_ref_concept_bridge(cb, _rel_repo(concept_bridge_path)))

    if subgraph_router_path and subgraph_router_path.is_file():
        inputs_manifest["subgraph_graphrag_router"] = _manifest_entry(subgraph_router_path)
        router = _read_json(subgraph_router_path)
        if router and router.get("schema") == "logos_subgraph_graphrag_router_v1":
            cross_refs.append(_cross_ref_subgraph_router(router, _rel_repo(subgraph_router_path)))

    lens_snapshots: list[dict[str, Any]] = []
    for row in fusion.get("inputs") or []:
        if isinstance(row, dict):
            ap = row.get("artifact_path")
            rel_ap = ap
            if isinstance(ap, str) and ap:
                try:
                    rel_ap = Path(ap).resolve().relative_to(ROOT.resolve()).as_posix()
                except ValueError:
                    rel_ap = ap
            lens_snapshots.append(
                {
                    "lens_id": row.get("lens_id"),
                    "available": row.get("available"),
                    "direction_score": row.get("direction_score"),
                    "confidence": row.get("confidence"),
                    "direction_sign": row.get("direction_sign"),
                    "artifact_path": rel_ap,
                }
            )

    conflict_summary = fusion.get("conflict_summary")
    if not isinstance(conflict_summary, dict):
        conflict_summary = {}

    return {
        "schema": "logos_cross_domain_interface_v1",
        "version": CDIM_VERSION,
        "ts_utc": _now_utc(),
        "labels": ["HYPO", "NON_GATING", "research_only"],
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "observation_only",
        "field_regime_id": field_regime_id,
        "lens_snapshots": lens_snapshots,
        "cross_refs": cross_refs,
        "conflict_summary": conflict_summary,
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
        "inputs_manifest": inputs_manifest,
        "design_doc": DESIGN_DOC,
        "fusion_stub_version": fusion.get("version"),
        "no_verse_level_ohaeng_ingest": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble logos cross-domain interface v1 (read-only).")
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--cross-rag-json", type=Path, default=DEFAULT_CROSS_RAG)
    ap.add_argument("--state-mapping-json", type=Path, default=DEFAULT_STATE_MAP)
    ap.add_argument("--concept-bridge-json", type=Path, default=DEFAULT_CONCEPT_BRIDGE)
    ap.add_argument("--bridge-registry-json", type=Path, default=DEFAULT_BRIDGE_REGISTRY)
    ap.add_argument("--subgraph-router-json", type=Path, default=DEFAULT_SUBGRAPH_ROUTER)
    ap.add_argument("--field-regime-id", default="observational_stub_non_gating")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-cross-rag", action="store_true")
    ap.add_argument("--no-state-mapping", action="store_true")
    ap.add_argument("--no-concept-bridge", action="store_true")
    ap.add_argument(
        "--use-bridge-registry",
        action="store_true",
        help="load all present bridges from registry instead of single concept-bridge-json",
    )
    ap.add_argument("--no-subgraph-router", action="store_true")
    ap.add_argument("--validate", action="store_true", help="jsonschema validate against CDIM schema")
    args = ap.parse_args()

    concept_bridge = None if args.no_concept_bridge else args.concept_bridge_json
    bridge_registry = None
    if args.use_bridge_registry and not args.no_concept_bridge:
        bridge_registry = args.bridge_registry_json
        concept_bridge = None

    doc = assemble(
        fusion_path=args.fusion_json,
        cross_rag_path=None if args.no_cross_rag else args.cross_rag_json,
        state_map_path=None if args.no_state_mapping else args.state_mapping_json,
        concept_bridge_path=concept_bridge,
        bridge_registry_path=bridge_registry,
        subgraph_router_path=None if args.no_subgraph_router else args.subgraph_router_json,
        field_regime_id=args.field_regime_id,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": _rel_repo(args.output), "cross_refs": len(doc["cross_refs"])}, ensure_ascii=False))

    if args.validate:
        jsonschema = __import__("jsonschema")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(doc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
