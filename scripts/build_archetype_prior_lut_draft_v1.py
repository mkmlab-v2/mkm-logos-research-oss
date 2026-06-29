#!/usr/bin/env python3
"""[HYPO] Draft finite LUT stats from nav frame + concept_bridge registry (human signoff pending)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VERSE_REF_RE = re.compile(r"verse:([A-Za-z0-9_.:]+)", re.I)
PROBE_DEFAULT = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.nextgen_archetype_prior_terms_v1 import (  # noqa: E402
    terms_from_concept_bridge,
    terms_from_nav_frame,
)

NAV_DEFAULT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
REGISTRY_DEFAULT = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_registry_nodes(registry: dict[str, Any]) -> dict[str, Any]:
    node_ids: set[str] = set()
    path_total = 0
    present = 0
    for entry in registry.get("entries") or []:
        if not entry.get("present"):
            continue
        present += 1
        path_total += int(entry.get("path_count") or 0)
        p = ROOT / str(entry.get("artifact_path", ""))
        if not p.is_file():
            continue
        bridge = json.loads(p.read_text(encoding="utf-8-sig"))
        for node in bridge.get("nodes") or []:
            if isinstance(node, dict) and node.get("node_id"):
                node_ids.add(str(node["node_id"]))
    return {
        "bridge_present_count": present,
        "path_edge_count_sum": path_total,
        "unique_node_id_count": len(node_ids),
    }


def _staging_from_de_probe(probe: dict[str, Any]) -> dict[str, Any]:
    """Attach DE hit evidence for commander LUT review; does not wire codec."""
    by_probe: dict[str, Any] = {}
    doc_ids: set[str] = set()
    verse_refs: set[str] = set()
    for pr in probe.get("probes") or []:
        if not isinstance(pr, dict):
            continue
        pid = str(pr.get("probe_id", ""))
        slim_hits = []
        for h in pr.get("hits") or []:
            if not isinstance(h, dict):
                continue
            did = h.get("document_id")
            if did:
                doc_ids.add(str(did))
            snips = []
            for sn in h.get("snippets") or []:
                snips.append(str(sn)[:400])
                for m in VERSE_REF_RE.findall(str(sn)):
                    verse_refs.add(m)
            slim_hits.append(
                {
                    "document_id": did,
                    "title": h.get("title"),
                    "link": h.get("link"),
                    "snippet_preview": snips[:2],
                }
            )
        by_probe[pid] = {
            "label_ko": pr.get("label_ko"),
            "concept_id": pr.get("concept_id"),
            "node_id": pr.get("node_id"),
            "hit_count": pr.get("hit_count"),
            "hits": slim_hits,
            "candidate_anchor_status": "pending_human_review",
        }
    return {
        "schema": "de_probe_lut_staging_v1",
        "probe_pointer": "reports/ng40_de_logos_anchor_probe_v1_latest.json",
        "probe_generated_at_utc": probe.get("generated_at_utc"),
        "unique_document_ids": len(doc_ids),
        "verse_refs_extracted": sorted(verse_refs),
        "candidates_by_probe_id": by_probe,
        "wired_into_codec": False,
        "human_reviewed": False,
        "note_ko": "DE RAG 후보; verse_refs는 스니펫 regex 추출만 — 확정은 지휘관",
    }


def _staging_from_llm_synthesis(
    doc: dict[str, Any],
    *,
    schema: str,
    pointer: str,
    provider_note_ko: str,
) -> dict[str, Any]:
    """Azure or NVIDIA NIM anchor candidates from DE probe hits (NON_GATING)."""
    by_probe: dict[str, Any] = {}
    verse_refs: set[str] = set()
    for row in doc.get("syntheses") or []:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("probe_id", ""))
        syn = row.get("synthesis") if isinstance(row.get("synthesis"), dict) else {}
        anchors = syn.get("anchor_candidates") or []
        for a in anchors:
            if isinstance(a, dict) and a.get("label"):
                verse_refs.add(str(a["label"]))
        for v in syn.get("verse_refs_guess") or []:
            verse_refs.add(str(v))
        for v in row.get("verse_refs_merged") or []:
            verse_refs.add(str(v))
        by_probe[pid] = {
            "label_ko": row.get("label_ko"),
            "status": row.get("status"),
            "anchor_candidates": anchors[:8],
            "human_review_note": syn.get("human_review_note"),
            "non_gating_disclaimer": syn.get("non_gating_disclaimer"),
            "candidate_anchor_status": "pending_human_review",
        }
    return {
        "schema": schema,
        "pointer": pointer,
        "generated_at_utc": doc.get("generated_at_utc"),
        "deployment": doc.get("deployment") or doc.get("model"),
        "verse_refs_guess": sorted(verse_refs),
        "candidates_by_probe_id": by_probe,
        "wired_into_codec": False,
        "human_reviewed": False,
        "note_ko": provider_note_ko,
    }


def _staging_from_azure_synthesis(azure: dict[str, Any]) -> dict[str, Any]:
    return _staging_from_llm_synthesis(
        azure,
        schema="azure_openai_anchor_staging_v1",
        pointer="reports/ng40_de_probe_azure_openai_synthesis_v1_latest.json",
        provider_note_ko="Azure OpenAI [HYPO] 요약; 확정·LUT 반영은 지휘관만",
    )


def _staging_from_nim_synthesis(nim: dict[str, Any]) -> dict[str, Any]:
    return _staging_from_llm_synthesis(
        nim,
        schema="nim_anchor_staging_v1",
        pointer="reports/ng40_de_probe_nim_synthesis_v1_latest.json",
        provider_note_ko="NVIDIA NIM [HYPO] 요약; 확정·LUT 반영은 지휘관만",
    )


def build_lut_draft(
    *,
    nav: dict[str, Any],
    registry: dict[str, Any] | None,
    de_probe: dict[str, Any] | None = None,
    azure_synthesis: dict[str, Any] | None = None,
    nim_synthesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = nav.get("navigation_graph") or {}
    archetype_n = len(graph.get("archetype_nodes") or [])
    edge_n = len(graph.get("edges") or [])
    anchor_n = len(nav.get("modern_concept_anchors") or [])
    reg_stats = _count_registry_nodes(registry) if registry else {}
    salience_terms: set[str] = set(terms_from_nav_frame(nav))
    if registry:
        for entry in registry.get("entries") or []:
            if not entry.get("present"):
                continue
            p = ROOT / str(entry.get("artifact_path", ""))
            if p.is_file():
                salience_terms |= terms_from_concept_bridge(
                    json.loads(p.read_text(encoding="utf-8-sig"))
                )
    finite_estimate = (
        reg_stats.get("unique_node_id_count", 0) + archetype_n + anchor_n
    )
    draft: dict[str, Any] = {
        "schema": "archetype_prior_lut_draft_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "human_reviewed": False,
        "human_signoff_required": True,
        "status": "draft_pending_commander_signoff",
        "nav_frame_pointer": "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json",
        "registry_pointer": "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
        "counts": {
            "archetype_graph_nodes": archetype_n,
            "archetype_graph_edges": edge_n,
            "modern_concept_anchors": anchor_n,
            "registry_bridge_present": reg_stats.get("bridge_present_count", 0),
            "registry_unique_node_ids": reg_stats.get("unique_node_id_count", 0),
            "registry_path_edges_sum": reg_stats.get("path_edge_count_sum", 0),
            "salience_term_tokens_estimate": len(salience_terms),
            "finite_node_count_estimate": finite_estimate,
        },
        "spatial_map_coordinates": {
            "status": "TBD",
            "note_ko": "좌표계는 지휘관 LUT 확정 후; 현재는 concept_id + node_id 유한 집합만",
        },
        "governance": {
            "tariff_bridge_human_reviewed": False,
            "semiconductor_bridge_human_reviewed": True,
            "registry_human_reviewed_ratio": registry.get("human_reviewed_ratio")
            if registry
            else None,
        },
    }
    if de_probe:
        draft["de_probe_staging_v1"] = _staging_from_de_probe(de_probe)
        draft["counts"]["de_probe_unique_documents"] = draft["de_probe_staging_v1"][
            "unique_document_ids"
        ]
        draft["counts"]["de_probe_verse_refs_extracted"] = len(
            draft["de_probe_staging_v1"]["verse_refs_extracted"]
        )
    if azure_synthesis:
        draft["azure_openai_anchor_staging_v1"] = _staging_from_azure_synthesis(
            azure_synthesis
        )
        draft["counts"]["azure_anchor_probe_count"] = len(
            draft["azure_openai_anchor_staging_v1"]["candidates_by_probe_id"]
        )
        draft["counts"]["azure_verse_refs_guess"] = len(
            draft["azure_openai_anchor_staging_v1"]["verse_refs_guess"]
        )
        if de_probe and "de_probe_staging_v1" in draft:
            merged = set(draft["de_probe_staging_v1"]["verse_refs_extracted"])
            if "azure_openai_anchor_staging_v1" in draft:
                merged |= set(draft["azure_openai_anchor_staging_v1"]["verse_refs_guess"])
            draft["de_probe_staging_v1"]["verse_refs_merged_with_azure"] = sorted(merged)
            draft["counts"]["verse_refs_merged_de_plus_azure"] = len(merged)
    if nim_synthesis:
        draft["nim_anchor_staging_v1"] = _staging_from_nim_synthesis(nim_synthesis)
        draft["counts"]["nim_verse_refs_guess"] = len(
            draft["nim_anchor_staging_v1"]["verse_refs_guess"]
        )
        if de_probe and "de_probe_staging_v1" in draft:
            merged = sorted(
                set(draft["de_probe_staging_v1"].get("verse_refs_extracted") or [])
                | set(draft["nim_anchor_staging_v1"]["verse_refs_guess"])
                | set(
                    draft.get("azure_openai_anchor_staging_v1", {}).get(
                        "verse_refs_guess"
                    )
                    or []
                )
            )
            draft["de_probe_staging_v1"]["verse_refs_merged_with_llm"] = merged
            draft["counts"]["verse_refs_merged_de_plus_llm"] = len(merged)
    return draft


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nav-json", type=Path, default=NAV_DEFAULT)
    ap.add_argument("--registry-json", type=Path, default=REGISTRY_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--patch-nav-frame", action="store_true")
    ap.add_argument(
        "--de-probe-json",
        type=Path,
        default=None,
        help="Merge ng40_de_logos_anchor_probe hits into de_probe_staging_v1 (no codec wire)",
    )
    ap.add_argument(
        "--azure-synthesis-json",
        type=Path,
        default=None,
        help="Path A: merge Azure OpenAI anchor staging (no codec wire)",
    )
    ap.add_argument(
        "--nim-synthesis-json",
        type=Path,
        default=None,
        help="NVIDIA NIM anchor staging from DE probe (no codec wire)",
    )
    args = ap.parse_args()
    if not args.nav_json.is_file():
        print(json.dumps({"error": "missing_nav_frame"}))
        return 2
    nav = json.loads(args.nav_json.read_text(encoding="utf-8-sig"))
    registry = (
        json.loads(args.registry_json.read_text(encoding="utf-8-sig"))
        if args.registry_json.is_file()
        else None
    )
    de_probe = None
    probe_path = args.de_probe_json or (
        PROBE_DEFAULT if PROBE_DEFAULT.is_file() else None
    )
    if probe_path and probe_path.is_file():
        de_probe = json.loads(probe_path.read_text(encoding="utf-8-sig"))
    azure_synthesis = None
    azure_path = args.azure_synthesis_json
    if azure_path and azure_path.is_file():
        azure_synthesis = json.loads(azure_path.read_text(encoding="utf-8-sig"))
    nim_synthesis = None
    nim_path = args.nim_synthesis_json
    if nim_path and nim_path.is_file():
        nim_synthesis = json.loads(nim_path.read_text(encoding="utf-8-sig"))
    draft = build_lut_draft(
        nav=nav,
        registry=registry,
        de_probe=de_probe,
        azure_synthesis=azure_synthesis,
        nim_synthesis=nim_synthesis,
    )
    if args.out_json.is_file():
        prev = json.loads(args.out_json.read_text(encoding="utf-8-sig"))
        if prev.get("status") == "commander_approved_v1":
            for key in (
                "human_reviewed",
                "human_signoff_required",
                "status",
                "commander_signoff_utc",
                "commander_signoff_by",
            ):
                if key in prev:
                    draft[key] = prev[key]
        if prev.get("de_nim_commander_anchor_signoff_v1"):
            draft["de_nim_commander_anchor_signoff_v1"] = prev[
                "de_nim_commander_anchor_signoff_v1"
            ]
            decisions = (prev["de_nim_commander_anchor_signoff_v1"] or {}).get(
                "decisions"
            ) or {}
            accepted = {p for p, d in decisions.items() if d == "accept"}
            for block_key in ("nim_anchor_staging_v1", "de_probe_staging_v1"):
                block = draft.get(block_key) or {}
                by_probe = block.get("candidates_by_probe_id") or {}
                for pid, decision in decisions.items():
                    row = by_probe.get(pid)
                    if not isinstance(row, dict):
                        continue
                    row["candidate_anchor_status"] = (
                        "commander_accepted_staging_v1"
                        if decision == "accept"
                        else "commander_rejected_staging_v1"
                    )
                if block:
                    draft[block_key] = block
            if prev.get("codec_wired_staging") or prev.get("lut_codec_staging_wire_v1"):
                for block_key in ("nim_anchor_staging_v1", "de_probe_staging_v1"):
                    block = draft.get(block_key)
                    if isinstance(block, dict):
                        block["wired_into_codec"] = True
                        block["codec_wire_mode"] = "staging_product_lane_only_v1"
                        block["track_a_active_write"] = False
                        for pid, row in (block.get("candidates_by_probe_id") or {}).items():
                            if isinstance(row, dict) and pid in accepted:
                                row["codec_staging_wired"] = True
                                row["codec_wire_lane"] = "hybrid_sidecar_preview"
                draft["lut_codec_staging_wire_v1"] = prev.get("lut_codec_staging_wire_v1")
                draft["codec_wired_staging"] = prev.get("codec_wired_staging", True)
                draft["track_a_active_write"] = False
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.patch_nav_frame:
        nav["lut"] = {
            "status": "draft_pending_commander_signoff",
            "finite_node_count": draft["counts"]["finite_node_count_estimate"],
            "draft_pointer": str(
                args.out_json.relative_to(ROOT)
            ).replace("\\", "/"),
            "spatial_map_coordinates": "TBD",
            "note_ko": "LUT 초안 집계 완료; 좌표·승인은 지휘관 검토 후",
        }
        args.nav_json.write_text(
            json.dumps(nav, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "finite_node_count_estimate": draft["counts"]["finite_node_count_estimate"],
                "de_probe_merged": de_probe is not None,
                "de_probe_verse_refs": draft["counts"].get("de_probe_verse_refs_extracted"),
                "azure_synthesis_merged": azure_synthesis is not None,
                "nim_synthesis_merged": nim_synthesis is not None,
                "azure_verse_refs": draft["counts"].get("azure_verse_refs_guess"),
                "nim_verse_refs": draft["counts"].get("nim_verse_refs_guess"),
                "verse_refs_merged_de_plus_llm": draft["counts"].get(
                    "verse_refs_merged_de_plus_llm"
                ),
                "patched_nav": args.patch_nav_frame,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
