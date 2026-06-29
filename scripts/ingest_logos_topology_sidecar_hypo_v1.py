#!/usr/bin/env python3
"""Ingest external Deep Research topology sidecar into isolated Layer A artifact ([HYPO]).

Does NOT merge into logos_cosmic_anchor_batch_v1 or canon fabric.

Reproducible:
  py scripts/ingest_logos_topology_sidecar_hypo_v1.py \\
    --input data/logos/topology_sidecar_job_suffering_hypo_v1.seed.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_topology_sidecar_hypo_v1.schema.json"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
REPORT = ROOT / "docs/final/artifacts/logos_topology_sidecar_ingest_v1_latest.json"

REQUIRED_TOP = frozenset(
    {
        "schema",
        "hypothesis_class",
        "research_only",
        "non_gating",
        "send_gate",
        "track_a_blocked",
        "materialize_canon",
        "query_id",
        "query_ko",
        "anchor_ref",
        "external_source",
        "anchor_matrix",
        "narrative_route",
        "bridge_pivot",
        "reading_pack",
        "intentional_causal_gap",
    }
)

VERSE_REF_OK = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+(-\d+)?$")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _out_path(query_id: str) -> Path:
    return ROOT / f"docs/final/artifacts/logos_topology_sidecar_{query_id}_v1_latest.json"


def _collect_verse_refs(doc: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for node in doc.get("anchor_matrix") or []:
        refs.extend(node.get("verse_refs") or [])
    for stage in doc.get("narrative_route") or []:
        refs.extend(stage.get("verse_refs") or [])
    bridge = doc.get("bridge_pivot") or {}
    if bridge.get("verse_ref"):
        refs.append(str(bridge["verse_ref"]))
    refs.extend(bridge.get("secondary_refs") or [])
    if doc.get("anchor_ref"):
        refs.append(str(doc["anchor_ref"]))
    return refs


def _validate_governance(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "logos_topology_sidecar_hypo_v1":
        errors.append("schema must be logos_topology_sidecar_hypo_v1")
    if doc.get("hypothesis_class") != "HYPO":
        errors.append("hypothesis_class must be HYPO")
    if doc.get("research_only") is not True:
        errors.append("research_only must be true")
    if doc.get("non_gating") is not True:
        errors.append("non_gating must be true")
    if doc.get("send_gate") != "HOLD":
        errors.append("send_gate must be HOLD")
    if doc.get("track_a_blocked") is not True:
        errors.append("track_a_blocked must be true")
    if doc.get("materialize_canon") is not False:
        errors.append("materialize_canon must be false")
    gap = doc.get("intentional_causal_gap") or {}
    if gap.get("why_question_assembled") is not False:
        errors.append("intentional_causal_gap.why_question_assembled must be false")
    ext = doc.get("external_source") or {}
    if ext.get("ingest_mode") != "topology_sidecar":
        errors.append("external_source.ingest_mode must be topology_sidecar")
    return errors


def _validate_structure(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_TOP - set(doc)
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
    if not doc.get("query_id"):
        errors.append("query_id empty")
    if not isinstance(doc.get("anchor_matrix"), list) or not doc["anchor_matrix"]:
        errors.append("anchor_matrix must be non-empty list")
    if not isinstance(doc.get("narrative_route"), list) or not doc["narrative_route"]:
        errors.append("narrative_route must be non-empty list")
    if not isinstance(doc.get("reading_pack"), list) or not doc["reading_pack"]:
        errors.append("reading_pack must be non-empty list")
    for pack in doc.get("reading_pack") or []:
        if not isinstance(pack, dict):
            continue
        md_rel = pack.get("deep_synthesis_md_path")
        if md_rel:
            md_path = ROOT / str(md_rel)
            if not md_path.is_file():
                errors.append(f"deep_synthesis_md_path missing: {md_rel}")
    orders = [s.get("order") for s in doc.get("narrative_route") or [] if isinstance(s, dict)]
    if orders and sorted(orders) != list(range(1, len(orders) + 1)):
        errors.append("narrative_route order must be 1..N contiguous")
    return errors


def _router_verse_set() -> set[str]:
    if not ROUTER.is_file():
        return set()
    router = _load_json(ROUTER)
    out: set[str] = set()
    for raw in router.get("verse_ids") or []:
        canon = canonical_verse_ref(str(raw))
        if canon:
            out.add(canon)
    return out


def canonical_verse_ref(raw: str) -> str:
    from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref as canon

    return canon(raw)


def corpus_cross_check(doc: dict[str, Any]) -> dict[str, Any]:
    router_set = _router_verse_set()
    format_errors: list[str] = []
    router_linked: list[str] = []
    book_job: list[str] = []
    corpus_gap: list[dict[str, str]] = []

    seen: set[str] = set()
    for raw in _collect_verse_refs(doc):
        ref = canonical_verse_ref(raw)
        if not ref or not VERSE_REF_OK.match(ref.split("-")[0]):
            format_errors.append(raw)
            continue
        base = ref.split("-")[0]
        if base in seen:
            continue
        seen.add(base)
        if base in router_set:
            router_linked.append(base)
        elif base.startswith("Job."):
            book_job.append(base)
        else:
            corpus_gap.append(
                {
                    "ref": base,
                    "note_ko": "router verse_ids 미연결 — gap 태깅, ingest는 계속 [HYPO]",
                }
            )

    return {
        "router_verse_ids_loaded": len(router_set),
        "refs_total": len(seen),
        "corpus_router_linked": sorted(router_linked),
        "corpus_book_job": sorted(book_job),
        "corpus_gap": corpus_gap,
        "format_errors": sorted(set(format_errors)),
    }


def validate_topology_sidecar(doc: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors = _validate_governance(doc) + _validate_structure(doc)
    cross = corpus_cross_check(doc)
    if cross["format_errors"]:
        errors.append(f"verse ref format errors: {cross['format_errors']}")
    return errors, cross


def ingest(
    *,
    input_path: Path,
    dry_run: bool = False,
    out_path: Path | None = None,
) -> dict[str, Any]:
    doc = _load_json(input_path)
    errors, cross = validate_topology_sidecar(doc)
    if errors:
        raise SystemExit("\n".join(errors))

    query_id = str(doc["query_id"])
    target = out_path or _out_path(query_id)
    ingested = {
        "schema": "logos_topology_sidecar_ingested_v1",
        "sidecar_schema": "logos_topology_sidecar_hypo_v1",
        "ingested_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "materialize_canon": False,
        "input_path": input_path.relative_to(ROOT).as_posix(),
        "output_path": target.relative_to(ROOT).as_posix(),
        "query_id": query_id,
        "query_ko": doc.get("query_ko"),
        "anchor_ref": canonical_verse_ref(str(doc.get("anchor_ref") or "")),
        "reading_pack_count": len(doc.get("reading_pack") or []),
        "anchor_matrix_count": len(doc.get("anchor_matrix") or []),
        "narrative_route_count": len(doc.get("narrative_route") or []),
        "corpus_cross_check": cross,
        "topology": doc,
    }

    report = {
        "schema": "logos_topology_sidecar_ingest_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "materialize_canon": False,
        "input_path": input_path.relative_to(ROOT).as_posix(),
        "output_path": target.relative_to(ROOT).as_posix(),
        "query_id": query_id,
        "corpus_cross_check": cross,
        "reading_pack_count": ingested["reading_pack_count"],
        "reproducible_command": (
            "py scripts/run_logos_topology_sidecar_ingest_chain_v1.py "
            f"--input {input_path.relative_to(ROOT).as_posix()}"
        ),
    }

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(ingested, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not input_path.is_file():
        print(f"Missing input: {input_path}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.is_file():
        print(f"Missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2
    report = ingest(input_path=input_path, dry_run=args.dry_run, out_path=args.out)
    print(f"WROTE: {REPORT if not args.dry_run else '(dry-run)'}")
    print(
        f"  query_id={report['query_id']} reading_pack={report['reading_pack_count']} "
        f"router_linked={len(report['corpus_cross_check']['corpus_router_linked'])} "
        f"gap={len(report['corpus_cross_check']['corpus_gap'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
