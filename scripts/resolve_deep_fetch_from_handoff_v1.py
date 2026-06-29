#!/usr/bin/env python3
"""Resolve LTM graph concept coordinates from deep handoff envelope (Pillar A, max 3 paths)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_cursor_continuity_ssot_v1 import merge_deep_fetch_queue  # noqa: E402
from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    DEFAULT_GRAPH_PATH,
    load_graph,
    route_concepts_by_query,
)

DEFAULT_ENVELOPE = ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json"
DEFAULT_ENVELOPE_REPORTS = ROOT / "reports/mkm_cursor_deep_handoff_envelope_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/mkm_deep_fetch_resolve_smoke_v1_latest.json"

CONCEPT_ID_ALIASES: dict[str, str] = {
    "ltm_graph_meta": "ltm_graph_self_meta",
}

PHI_DENY_FRAGMENTS = (
    "lee_bomi",
    "kim_areum",
    "patient_track_b",
    "resolve_patient_clinical",
    "han_physician_clinical",
    "clinic_kakao_postpartum",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_denied_path(path: str, *, clinical_gated: bool) -> bool:
    if clinical_gated:
        return False
    low = path.lower().replace("\\", "/")
    return any(frag in low for frag in PHI_DENY_FRAGMENTS)


def _normalize_concept_id(concept_id: str) -> str:
    cid = concept_id.strip()
    return CONCEPT_ID_ALIASES.get(cid, cid)


def concept_paths(graph: dict[str, Any], concept_id: str) -> list[str]:
    cid = _normalize_concept_id(concept_id)
    concept = (graph.get("concepts") or {}).get(cid)
    if not isinstance(concept, dict):
        return []
    paths: list[str] = []
    primary = concept.get("primary_coordinate")
    if isinstance(primary, dict):
        fp = str(primary.get("file_path") or "").strip()
        if fp:
            paths.append(fp.replace("\\", "/"))
    for coord in concept.get("coordinates") or []:
        if not isinstance(coord, dict):
            continue
        fp = str(coord.get("file_path") or "").strip()
        if fp and fp.replace("\\", "/") not in paths:
            paths.append(fp.replace("\\", "/"))
    return paths


def build_query_from_envelope(envelope: dict[str, Any]) -> str:
    parts: list[str] = []
    for cid in envelope.get("ltm_concept_ids") or []:
        parts.append(str(cid).replace("_", " "))
    handoff = envelope.get("shallow_handoff") if isinstance(envelope.get("shallow_handoff"), dict) else {}
    hint = handoff.get("lens_route_hint") if isinstance(handoff.get("lens_route_hint"), dict) else {}
    lens_id = str(hint.get("lens_id") or "").strip()
    if lens_id:
        parts.append(lens_id)
    for anchor in handoff.get("anchor_ids") or []:
        parts.append(str(anchor))
    lane = str(envelope.get("lane") or "").strip()
    if lane:
        parts.append(lane)
    return " ".join(parts).strip()


def resolve_deep_fetch(
    envelope: dict[str, Any],
    graph: dict[str, Any],
    *,
    clinical_gated: bool = False,
    max_paths: int = 3,
) -> dict[str, Any]:
    if envelope.get("graph_axis") not in (None, "A_ltm"):
        raise ValueError("envelope graph_axis must be A_ltm for this resolver")

    concept_ids: list[str] = []
    for raw in envelope.get("ltm_concept_ids") or []:
        cid = _normalize_concept_id(str(raw))
        if cid and cid not in concept_ids:
            concept_ids.append(cid)

    query = build_query_from_envelope(envelope)
    if query:
        for cid, _concept in route_concepts_by_query(graph, query, max_concepts=5):
            if cid not in concept_ids:
                concept_ids.append(cid)

    resolved: list[dict[str, Any]] = []
    denied: list[str] = []
    seen: set[str] = set()

    def _try_add(path: str, *, concept_id: str | None = None, source: str) -> None:
        norm = path.replace("\\", "/")
        if norm in seen:
            return
        if _is_denied_path(norm, clinical_gated=clinical_gated):
            denied.append(norm)
            return
        seen.add(norm)
        entry: dict[str, Any] = {"path": norm, "source": source}
        if concept_id:
            entry["concept_id"] = concept_id
        resolved.append(entry)

    for cid in concept_ids:
        for path in concept_paths(graph, cid):
            _try_add(path, concept_id=cid, source="ltm_graph")
            if len(resolved) >= max_paths:
                break
        if len(resolved) >= max_paths:
            break

    if len(resolved) < max_paths:
        for path in envelope.get("deep_fetch_next") or []:
            _try_add(str(path), source="envelope_queue")
            if len(resolved) >= max_paths:
                break

    return {
        "schema": "mkm_deep_fetch_resolve_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "graph_axis": "A_ltm",
        "lane": envelope.get("lane"),
        "continuity_id": envelope.get("continuity_id"),
        "concept_ids": concept_ids,
        "paths": [item["path"] for item in resolved[:max_paths]],
        "resolved": resolved[:max_paths],
        "denied_paths": denied,
        "clinical_gated": clinical_gated,
        "query_built": query,
        "reproducible_command": (
            "py scripts/resolve_deep_fetch_from_handoff_v1.py "
            f"--lane {envelope.get('lane') or 'infra'}"
        ),
    }


def patch_envelope_with_resolve(
    envelope_path: Path,
    resolved: dict[str, Any],
    *,
    reports_copy: Path | None = None,
) -> dict[str, Any]:
    envelope = _read_json(envelope_path)
    graph_paths = list(resolved.get("paths") or [])
    if not graph_paths:
        raise ValueError("resolved paths empty — cannot patch envelope")

    merged_queue = merge_deep_fetch_queue(
        graph_paths,
        list(envelope.get("deep_fetch_next") or []),
    )
    envelope["graph_resolved_fetch"] = {
        "generated_at_utc": _utc_now(),
        "paths": graph_paths[:3],
        "concept_ids": list(resolved.get("concept_ids") or [])[:5],
        "query_built": str(resolved.get("query_built") or ""),
    }
    envelope["deep_fetch_next"] = merged_queue
    read_order = list(envelope.get("read_order") or [])
    if read_order:
        head = read_order[:4]
        tail = [p for p in graph_paths[:3] if p not in head]
        envelope["read_order"] = head + tail

    text = json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"
    envelope_path.parent.mkdir(parents=True, exist_ok=True)
    envelope_path.write_text(text, encoding="utf-8")
    if reports_copy:
        reports_copy.parent.mkdir(parents=True, exist_ok=True)
        reports_copy.write_text(text, encoding="utf-8")
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envelope", type=Path, default=DEFAULT_ENVELOPE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--lane", default="", help="clinical-gated enables PHI paths")
    parser.add_argument("--clinical-gated", action="store_true")
    parser.add_argument("--max-paths", type=int, default=3)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--patch-envelope",
        action="store_true",
        help="Prepend graph-resolved paths into envelope deep_fetch_next (artifacts + reports).",
    )
    args = parser.parse_args()

    clinical_gated = args.clinical_gated or args.lane == "clinical-gated"
    if not args.envelope.is_file():
        print(f"FAIL: envelope missing: {args.envelope}", file=sys.stderr)
        return 1
    if not args.graph.is_file():
        print(f"FAIL: graph missing: {args.graph}", file=sys.stderr)
        return 1

    envelope = _read_json(args.envelope)
    if envelope.get("schema") != "mkm_cursor_deep_handoff_envelope_v1":
        print(f"FAIL: unexpected envelope schema: {envelope.get('schema')!r}", file=sys.stderr)
        return 1

    graph = load_graph(args.graph)
    doc = resolve_deep_fetch(
        envelope,
        graph,
        clinical_gated=clinical_gated,
        max_paths=max(1, min(args.max_paths, 3)),
    )
    if not doc["paths"]:
        print("FAIL: no paths resolved", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"paths={doc['paths']}")

    if args.patch_envelope:
        patched = patch_envelope_with_resolve(
            args.envelope,
            doc,
            reports_copy=DEFAULT_ENVELOPE_REPORTS,
        )
        print(f"PATCHED: {args.envelope} deep_fetch_next={len(patched.get('deep_fetch_next') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
