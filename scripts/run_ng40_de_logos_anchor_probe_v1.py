#!/usr/bin/env python3
"""[HYPO] Discovery Engine RAG probe for NG-40 Logos / biblical anchor candidates.

Uses nav_frame + modern_concept_anchors to run targeted Agent Search queries.
Output is human-review input for LUT / concept_bridge — NOT wired into ng40 codec.

Prereqs:
  py -m pip install "google-cloud-discoveryengine>=0.11.0"
  gcloud auth application-default login

Example:
  py scripts/run_ng40_de_logos_anchor_probe_v1.py --dry-run
  py scripts/run_ng40_de_logos_anchor_probe_v1.py --page-size 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NAV = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
DEFAULT_OUT = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
DEFAULT_PROJECT = "mkm-lab-agi-2025"
DEFAULT_ENGINE = "b2g-search-mkm-lab-agi-2025"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _serving_config(project: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_serving_config"
    )


def _queries_from_nav_frame(nav: dict[str, Any]) -> list[dict[str, Any]]:
    """Build fixed probe queries from nav_frame nodes and modern concepts."""
    probes: list[dict[str, Any]] = []
    graph = nav.get("navigation_graph") or {}
    for node in graph.get("archetype_nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("node_id", ""))
        label_ko = str(node.get("label_ko", ""))
        role = str(node.get("role", ""))
        en_hint = nid.replace("archetype:", "").replace("function:", "").replace("_", " ")
        query = f"{label_ko} {en_hint} Logos archetype biblical metaphor MKM"
        probes.append(
            {
                "probe_id": f"nav:{nid}",
                "source": "navigation_graph",
                "node_id": nid,
                "label_ko": label_ko,
                "role": role,
                "query": query.strip(),
            }
        )
    for item in nav.get("modern_concept_anchors") or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("concept_id", ""))
        bridge = item.get("bridge_artifact")
        concept_slug = cid.replace("concept:", "")
        query = f"{concept_slug} trade technology Logos concept bridge biblical anchor MKM"
        probes.append(
            {
                "probe_id": f"concept:{cid}",
                "source": "modern_concept_anchors",
                "concept_id": cid,
                "bridge_artifact": bridge,
                "human_reviewed_bridge": item.get("human_reviewed_bridge"),
                "query": query.strip(),
            }
        )
    return probes


def _hit_summary(hit_dict: dict[str, Any]) -> dict[str, Any]:
    doc = hit_dict.get("document") or {}
    struct = doc.get("derived_struct_data") or doc.get("derivedStructData") or {}
    if not isinstance(struct, dict):
        struct = {}
    title = struct.get("title") or struct.get("htmlTitle") or ""
    link = struct.get("link") or struct.get("uri") or ""
    snippets: list[str] = []
    for sn in struct.get("snippets") or []:
        if isinstance(sn, dict):
            text = sn.get("snippet") or sn.get("htmlSnippet") or ""
            if text:
                snippets.append(str(text)[:800])
    extractive = struct.get("extractive_answers") or struct.get("extractiveAnswers") or []
    for ex in extractive:
        if isinstance(ex, dict):
            content = ex.get("content") or ex.get("text") or ""
            if content:
                snippets.append(str(content)[:800])
    return {
        "document_id": doc.get("id") or doc.get("name"),
        "title": str(title)[:500] if title else None,
        "link": str(link)[:500] if link else None,
        "snippets": snippets[:5],
    }


def _search_probe(
    client: Any,
    SearchRequest: Any,
    *,
    serving: str,
    probe: dict[str, Any],
    page_size: int,
) -> dict[str, Any]:
    from google.protobuf.json_format import MessageToDict

    cs = SearchRequest.ContentSearchSpec(
        snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True,
            max_snippet_count=5,
            reference_only=False,
        ),
    )
    req = SearchRequest(
        serving_config=serving,
        query=probe["query"],
        page_size=page_size,
        content_search_spec=cs,
    )
    t0 = time.perf_counter()
    hits: list[dict[str, Any]] = []
    for hit in client.search(request=req):
        d = MessageToDict(hit._pb, preserving_proto_field_name=True)  # type: ignore[attr-defined]
        hits.append(_hit_summary(d))
        if len(hits) >= page_size:
            break
    return {
        **probe,
        "hit_count": len(hits),
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        "hits": hits,
        "candidate_anchor_status": "pending_human_review",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--location", default="global")
    p.add_argument("--engine-id", default=DEFAULT_ENGINE)
    p.add_argument("--nav-frame", type=Path, default=DEFAULT_NAV)
    p.add_argument("--page-size", type=int, default=5)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not args.nav_frame.is_file():
        print(f"nav_frame missing: {args.nav_frame}", file=sys.stderr)
        return 2

    nav = json.loads(args.nav_frame.read_text(encoding="utf-8-sig"))
    probes = _queries_from_nav_frame(nav)

    payload: dict[str, Any] = {
        "schema": "ng40_de_logos_anchor_probe_v1",
        "generated_at_utc": _utc_now(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "track_a_active_write": False,
        "gating_policy": "NON_GATING",
        "billing_surface": "discovery_engine",
        "credit_note": "Uses GenAI App Builder / Discovery Engine SKU; not Vertex AI",
        "project_id": args.project,
        "engine_id": args.engine_id,
        "nav_frame_pointer": str(args.nav_frame.relative_to(ROOT).as_posix()),
        "forbidden": [
            "auto_merge_hits_into_ng40_codec",
            "auto_merge_hits_into_lut_without_commander_signoff",
            "track_a_active_write",
            "live_trading_gating",
        ],
        "human_review_workflow": [
            "Review hits[].title/snippets per probe_id",
            "Map to verse_decoded_v2_single_anchor_v1.jsonl or concept_bridge JSON",
            "Run build_archetype_prior_lut_draft_v1.py after commander sign-off",
            "Re-run run_nextgen_hybrid_spine_logos_stack_v1.py to measure salience uplift",
        ],
        "lut_draft_pointer": nav.get("lut", {}).get("draft_pointer"),
        "probe_count": len(probes),
        "probes": [],
        "summary": {},
    }

    if args.dry_run:
        payload["dry_run"] = True
        payload["probes"] = [{k: v for k, v in pr.items() if k != "hits"} for pr in probes]
        payload["summary"] = {
            "verdict": "dry_run_planned",
            "planned_search_calls": len(probes),
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        print(f"wrote {args.out_json.relative_to(ROOT).as_posix()}")
        return 0

    try:
        from google.cloud.discoveryengine_v1 import SearchServiceClient
        from google.cloud.discoveryengine_v1.types import SearchRequest
    except ImportError:
        print(
            'Missing dependency: py -m pip install "google-cloud-discoveryengine>=0.11.0"',
            file=sys.stderr,
        )
        return 2

    serving = _serving_config(args.project, args.location, args.engine_id)
    client = SearchServiceClient()
    results: list[dict[str, Any]] = []
    ok = 0
    fail = 0
    for probe in probes:
        try:
            row = _search_probe(
                client,
                SearchRequest,
                serving=serving,
                probe=probe,
                page_size=max(1, args.page_size),
            )
            results.append(row)
            ok += 1
        except Exception as exc:  # noqa: BLE001 — probe must continue
            fail += 1
            results.append(
                {
                    **probe,
                    "hit_count": 0,
                    "hits": [],
                    "error": str(exc)[:500],
                    "candidate_anchor_status": "search_failed",
                }
            )

    payload["probes"] = results
    total_hits = sum(r.get("hit_count", 0) for r in results)
    payload["summary"] = {
        "probes_ok": ok,
        "probes_failed": fail,
        "total_hits": total_hits,
        "verdict": "probe_complete" if ok else "probe_failed",
        "next_step": "commander_human_review_before_lut",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {args.out_json.relative_to(ROOT).as_posix()}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
