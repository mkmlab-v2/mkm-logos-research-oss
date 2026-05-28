#!/usr/bin/env python3
"""Apply device_memory_bridge local_graph_update_hints onto pet local graph slice ([HYPO])."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/pet_companion_device_memory_bridge_v1_fixture.json"
DEFAULT_SLICE = ROOT / "docs/final/artifacts/pet_companion_local_graph_slice_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/pet_companion_local_graph_slice_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _node_id(label: str, prefix: str) -> str:
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in label)[:48]
    return f"{prefix}_{safe}"


def apply_hints(
    slice_doc: dict[str, Any],
    hints: dict[str, Any],
    *,
    profile_id: str,
    max_nodes: int,
    max_edges: int,
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {
        str(n.get("node_id")): n for n in (slice_doc.get("nodes") or []) if isinstance(n, dict) and n.get("node_id")
    }
    edges: list[dict[str, Any]] = list(slice_doc.get("edges") or [])

    prof_nid = _node_id(profile_id, "node_profile")
    if prof_nid not in nodes and len(nodes) < max_nodes:
        nodes[prof_nid] = {
            "node_id": prof_nid,
            "kind": "profile_ref",
            "label_ko": profile_id,
            "profile_id": profile_id,
        }

    for label in hints.get("suggested_nodes_to_upsert") or []:
        if len(nodes) >= max_nodes:
            break
        if not isinstance(label, str) or not label.strip():
            continue
        nid = _node_id(label, "node_hint")
        if nid not in nodes:
            nodes[nid] = {
                "node_id": nid,
                "kind": "observation_ref",
                "label_ko": label,
                "observation_id": nid,
                "source": "device_memory_bridge_hints",
            }

    for edge in hints.get("suggested_edges_to_link") or []:
        if len(edges) >= max_edges:
            break
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        if not src or not tgt:
            continue
        src_nid = _node_id(src, "node_hint") if src not in nodes else src
        tgt_nid = _node_id(tgt, "node_hint") if tgt not in nodes else tgt
        if src_nid not in nodes and len(nodes) < max_nodes:
            nodes[src_nid] = {"node_id": src_nid, "kind": "observation_ref", "label_ko": src, "observation_id": src_nid}
        if tgt_nid not in nodes and len(nodes) < max_nodes:
            nodes[tgt_nid] = {"node_id": tgt_nid, "kind": "observation_ref", "label_ko": tgt, "observation_id": tgt_nid}
        edges.append(
            {
                "source": src_nid,
                "target": tgt_nid,
                "relation": str(edge.get("relation") or "LINK"),
                "source_kind": "device_memory_bridge_hints",
            }
        )

    out = dict(slice_doc)
    out.update(
        {
            "schema": "pet_companion_local_graph_slice_v1",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "non_gating": True,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "max_nodes_cap": max_nodes,
            "max_edges_cap": max_edges,
            "nodes": list(nodes.values()),
            "edges": edges,
            "hints_applied": {
                "graph_hint_schema": hints.get("graph_hint_schema"),
                "nodes_upserted": list(hints.get("suggested_nodes_to_upsert") or []),
                "edges_linked": len(hints.get("suggested_edges_to_link") or []),
            },
            "policy": {
                "on_device_cap_enforced": len(nodes) <= max_nodes and len(edges) <= max_edges,
                "must_not_merge_with": ["logos_bible_subgraph", "mkm_ops_memory_graph"],
                "bridge_lane": "pet_companion_device_memory_bridge_v1",
            },
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture-json", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument(
        "--response-json",
        type=Path,
        default=None,
        help="Live or saved bridge response (overrides fixture mock_response)",
    )
    ap.add_argument(
        "--request-json",
        type=Path,
        default=None,
        help="Bridge request for profile_id (overrides fixture mock_request)",
    )
    ap.add_argument("--input-slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-nodes", type=int, default=128)
    ap.add_argument("--max-edges", type=int, default=140)
    args = ap.parse_args()

    fixture_path = args.fixture_json if args.fixture_json.is_absolute() else ROOT / args.fixture_json
    slice_path = args.input_slice_json if args.input_slice_json.is_absolute() else ROOT / args.input_slice_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    response_path = (
        args.response_json
        if args.response_json is None
        else (args.response_json if args.response_json.is_absolute() else ROOT / args.response_json)
    )
    request_path = (
        args.request_json
        if args.request_json is None
        else (args.request_json if args.request_json.is_absolute() else ROOT / args.request_json)
    )

    resp: dict[str, Any] = {}
    req: dict[str, Any] = {}
    if response_path and response_path.is_file():
        resp = _load_json(response_path) or {}
    if request_path and request_path.is_file():
        req = _load_json(request_path) or {}

    if not resp or not req:
        fixture = _load_json(fixture_path)
        if not fixture and (not resp or not req):
            print(json.dumps({"ok": False, "error": "missing fixture or response/request"}, ensure_ascii=False))
            return 2
        if fixture:
            if not resp:
                resp = fixture.get("mock_response") if isinstance(fixture.get("mock_response"), dict) else {}
            if not req:
                req = fixture.get("mock_request") if isinstance(fixture.get("mock_request"), dict) else {}
    hints = resp.get("local_graph_update_hints") if isinstance(resp.get("local_graph_update_hints"), dict) else {}
    if not hints:
        print(json.dumps({"ok": False, "error": "no local_graph_update_hints"}, ensure_ascii=False))
        return 2

    base = _load_json(slice_path) or {
        "schema": "pet_companion_local_graph_slice_v1",
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
    }
    profile_id = str(req.get("profile_id") or "pet-demo-001")
    doc = apply_hints(base, hints, profile_id=profile_id, max_nodes=max(1, args.max_nodes), max_edges=max(1, args.max_edges))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "node_count": doc["node_count"],
                "edge_count": doc["edge_count"],
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
