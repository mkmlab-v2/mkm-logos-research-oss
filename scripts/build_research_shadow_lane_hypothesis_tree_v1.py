#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Research Shadow Lane hypothesis tree — canon + satellite paths, human judgment [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "docs/final/artifacts/research_shadow_lane_seeds/job_prologue_suffering_v1.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/research_shadow_lane_hypothesis_tree_v1.schema.json"
DEFAULT_ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_research_shadow_lane_v1.json"
)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
RESOLVER = ROOT / "scripts/resolve_logos_verse_reference_v1.py"
APOCRYPHA_MANIFEST = (
    ROOT / "projects/dss-4d-ingest/outputs/apocrypha_quality_report_pilot_manifest_ext2.json"
)

SCHEMA_VERSION = "research_shadow_lane_hypothesis_tree_v1"
GENERATOR = "build_research_shadow_lane_hypothesis_tree_v1.py@1.0.0"

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "Research Shadow Lane 가설 트리입니다. [HYPO][NON_GATING] — 경로만 제시하며 "
        "「이유」의 최종 판단·신학적 단정·Track A·실매매 근거가 아닙니다. "
        "채택/기각은 지휘관(Human-in-the-Loop) 판단입니다."
    ),
}

PROLOGUE_CAUSALITY_REFS = frozenset(
    {"Job.1.6", "Job.1.8", "Job.1.12", "Job.2.3", "Job.2.6", "Job.2.10"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _fetch_corpus_row(ref: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "--text", ref, "--fetch-row"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"verse_id": ref, "found": False, "error": proc.stderr.strip()[:200]}
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verse_id": ref, "found": False, "error": "invalid_resolver_json"}
    rows = doc.get("corpus_rows") or []
    if not rows:
        return {"verse_id": ref, "found": False}
    row = rows[0]
    if not row.get("found"):
        return {"verse_id": ref, "found": False}
    inner = row.get("row") or {}
    text = str(inner.get("text") or inner.get("original_text") or "")[:240]
    return {
        "verse_id": ref,
        "found": True,
        "source_ref": inner.get("source_ref"),
        "edition": inner.get("edition"),
        "text_snippet": text,
        "decode_status": inner.get("decode_status"),
    }


def _cross_ref_has_job(cross_ref: dict[str, Any]) -> bool:
    rows = cross_ref.get("rows") or cross_ref.get("entries") or []
    for row in rows:
        blob = json.dumps(row, ensure_ascii=False)
        if "Job" in blob or "욥" in blob:
            return True
    return False


def _apocrypha_works_set() -> set[str]:
    if not APOCRYPHA_MANIFEST.is_file():
        return set()
    doc = _load(APOCRYPHA_MANIFEST)
    works = doc.get("works") or doc.get("work_counts") or {}
    if isinstance(works, dict):
        return {str(k).lower() for k in works}
    return set()


def _router_verse_ids(router: dict[str, Any] | None) -> list[str]:
    if not router:
        return []
    ids = router.get("verse_ids") or []
    return [str(x) for x in ids]


def _node(nid: str, label: str, kind: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"id": nid, "label": label, "kind": kind}
    row.update(extra)
    return row


def _edge(src: str, dst: str, edge_type: str = "supports", weight: float = 1.0) -> dict[str, Any]:
    return {"src": src, "dst": dst, "edge_type": edge_type, "weight": weight}


def _tag_canon(refs: list[str], canon_evidence: dict[str, dict[str, Any]]) -> str:
    if not refs:
        return "red"
    found = sum(1 for r in refs if canon_evidence.get(r, {}).get("found"))
    if found == len(refs):
        return "green"
    if found > 0:
        return "yellow"
    return "red"


def _tag_archaeology(literature_pointers: list[dict[str, Any]], cross_ref_job: bool) -> str:
    dss_ptrs = [p for p in literature_pointers if p.get("kind") == "dss"]
    if not dss_ptrs:
        return "red"
    if cross_ref_job:
        return "green"
    return "yellow"


def _tag_apocrypha(apocrypha_refs: list[str], works: set[str]) -> str:
    if not apocrypha_refs:
        return "red"
    for ref in apocrypha_refs:
        key = ref.lower().replace(" ", "_")
        if any(key in w or w in key for w in works):
            return "green"
    return "yellow"


def build_tree(
    seed: dict[str, Any],
    *,
    router: dict[str, Any] | None,
    cross_ref: dict[str, Any],
    query_id: str,
) -> dict[str, Any]:
    issue_id = str(seed["issue_id"])
    query_ko = str(seed["query_ko"])
    all_canon_refs: list[str] = list(seed.get("canon_refs") or [])
    for h in seed.get("hypothesis_seeds") or []:
        for r in h.get("canon_refs") or []:
            if r not in all_canon_refs:
                all_canon_refs.append(r)

    canon_evidence = {ref: _fetch_corpus_row(ref) for ref in all_canon_refs}
    cross_ref_job = _cross_ref_has_job(cross_ref)
    apocrypha_works = _apocrypha_works_set()
    router_ids = _router_verse_ids(router)
    prologue_in_router = [r for r in PROLOGUE_CAUSALITY_REFS if r in router_ids]

    hypotheses: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = [
        _node(
            "query::root",
            query_ko,
            "query",
            label_ko=query_ko,
            hub_score=1.0,
        ),
        _node(
            "gate::fact_lock",
            "Fact-Lock",
            "gate",
            label_ko="인과 단정 미조립",
            status="ACTIVE",
            hub_score=0.98,
        ),
        _node(
            "gate::send_hold",
            "SEND HOLD",
            "gate",
            label_ko="send_gate HOLD",
            status="HOLD",
            hub_score=0.95,
        ),
    ]
    edges: list[dict[str, Any]] = [
        _edge("query::root", "gate::fact_lock", "bounded_by"),
        _edge("gate::fact_lock", "gate::send_hold", "enforces"),
    ]

    for hseed in seed.get("hypothesis_seeds") or []:
        hid = str(hseed["hypothesis_id"])
        refs = [str(r) for r in (hseed.get("canon_refs") or [])]
        lit_ptrs = list(hseed.get("literature_pointers") or [])
        apo_refs = [str(r) for r in (hseed.get("apocrypha_refs") or [])]

        canon_tag = _tag_canon(refs, canon_evidence)
        arch_tag = _tag_archaeology(lit_ptrs, cross_ref_job)
        apo_tag = _tag_apocrypha(apo_refs, apocrypha_works)

        layers: list[dict[str, Any]] = []
        for ref in refs:
            ev = canon_evidence.get(ref, {"verse_id": ref, "found": False})
            layers.append(
                {
                    "layer": "canon_mt",
                    "ref": ref,
                    "in_repo": bool(ev.get("found")),
                    "tag": "green" if ev.get("found") else "red",
                    "text_snippet": ev.get("text_snippet"),
                }
            )
        for ptr in lit_ptrs:
            layers.append(
                {
                    "layer": str(ptr.get("kind") or "literature"),
                    "ref": ptr.get("ref"),
                    "in_repo": False,
                    "tag": "yellow",
                    "note_ko": ptr.get("note_ko"),
                }
            )
        for aref in apo_refs:
            in_pilot = any(aref.lower().replace(" ", "_") in w for w in apocrypha_works)
            layers.append(
                {
                    "layer": "apocrypha",
                    "ref": aref,
                    "in_repo": in_pilot,
                    "tag": "green" if in_pilot else "yellow",
                    "note_ko": "48k pilot manifest" if in_pilot else "literature_pointer_only",
                }
            )
        if hseed.get("router_observation") and router:
            layers.append(
                {
                    "layer": "router_observation",
                    "ref": "question_logos_subgraph_router",
                    "in_repo": True,
                    "tag": "green",
                    "router_verse_ids": router_ids[:20],
                    "prologue_causality_in_top": prologue_in_router,
                }
            )

        hyp = {
            "hypothesis_id": hid,
            "label_ko": hseed["label_ko"],
            "label_en": hseed.get("label_en"),
            "path_summary_ko": hseed.get("path_summary_ko"),
            "status": "path_only_not_verdict",
            "tags": {
                "canon": canon_tag,
                "archaeology": arch_tag,
                "apocrypha": apo_tag,
            },
            "evidence_layers": layers,
            "commander_prompt_ko": (
                f"가설 경로 「{hseed['label_ko']}」— 채택/기각/보류는 지휘관 판단. "
                "시스템은 단정하지 않습니다."
            ),
        }
        hypotheses.append(hyp)

        nid = f"hypo::{hid}"
        nodes.append(
            _node(
                nid,
                hseed["label_ko"][:48],
                "hypo",
                label_ko=hseed["label_ko"],
                hub_score=0.7,
                tags=hyp["tags"],
            )
        )
        edges.append(_edge("query::root", nid, "hypothesis_path"))
        for ref in refs:
            cid = f"canon::{ref}"
            if not any(n["id"] == cid for n in nodes):
                ev = canon_evidence.get(ref, {})
                nodes.append(
                    _node(
                        cid,
                        ref,
                        "fact",
                        label_ko=ref,
                        ref=ref,
                        status="found" if ev.get("found") else "missing",
                    )
                )
            edges.append(_edge(nid, cid, "cites_canon"))

    boundary_proof = {
        "router_verdict": "causal_narrative_not_assembled",
        "canon_lookup_available": any(v.get("found") for v in canon_evidence.values()),
        "verified_anchor": False,
        "prologue_causality_refs_in_router_top": prologue_in_router,
        "router_verse_ids_sample": router_ids[:14] if router else [],
        "cross_ref_job_rows_in_repo": cross_ref_job,
        "theme_lanes_active": list((router or {}).get("theme_lanes_active") or []),
    }

    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "issue_id": issue_id,
        "query_id": query_id,
        "query_ko": query_ko,
        "disclaimer": DISCLAIMER,
        "rail_status": {
            "send_gate": "HOLD",
            "verified_anchor_achieved": False,
            "lane": "track_b_research_shadow",
            "fact_lock_integrity": "active_no_causal_merge",
        },
        "boundary_proof": boundary_proof,
        "canon_evidence": [canon_evidence[r] for r in all_canon_refs if r in canon_evidence],
        "hypotheses": hypotheses,
        "judgment_slots": {
            "adopt_hypothesis_id": None,
            "reject_hypothesis_ids": [],
            "commander_note": None,
            "human_in_the_loop": True,
            "instruction_ko": "각 가설의 tags(녹/황/적)와 evidence_layers를 검토한 뒤 채택·기각·보류를 기록하세요.",
        },
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "hypothesis_count": len(hypotheses),
            "canon_refs_resolved": sum(1 for v in canon_evidence.values() if v.get("found")),
            "canon_refs_total": len(canon_evidence),
        },
        "reproduce": {
            "commands": [
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_hypo_generation_chain_v1.ps1 -IssueId job_prologue_suffering",
                f"py {RESOLVER.relative_to(ROOT).as_posix()} --text Job.2.3 --fetch-row",
            ],
            "seed_path": str(DEFAULT_SEED.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build research shadow lane hypothesis tree v1.")
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--cross-ref-json", type=Path, default=DEFAULT_CROSS_REF)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--query-id", default="job_suffering_reason")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()

    seed_path = args.seed_json if args.seed_json.is_absolute() else ROOT / args.seed_json
    router_path = args.router_json if args.router_json.is_absolute() else ROOT / args.router_json
    cross_path = args.cross_ref_json if args.cross_ref_json.is_absolute() else ROOT / args.cross_ref_json
    schema_path = args.schema if args.schema.is_absolute() else ROOT / args.schema
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_art = args.out_artifact if args.out_artifact.is_absolute() else ROOT / args.out_artifact

    seed = _load(seed_path)
    router = _load(router_path) if router_path.is_file() else None
    cross_ref = _load(cross_path) if cross_path.is_file() else {}

    doc = build_tree(seed, router=router, cross_ref=cross_ref, query_id=args.query_id)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_art.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    out_json.write_text(payload, encoding="utf-8")
    out_art.write_text(payload, encoding="utf-8")

    if not args.skip_validate:
        _validate(doc, schema_path)

    print(json.dumps({"ok": True, "out": str(out_json), "hypotheses": len(doc["hypotheses"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
