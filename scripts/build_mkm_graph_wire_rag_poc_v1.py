#!/usr/bin/env python3
"""DF-P0-01: Graph slice → reasoning path → wire envelope honest metrics PoC (research only)."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "logos_graph_wire_rag_poc_v1"
VERSION = "1.0.0"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _verse_atom_ids(graph: dict[str, Any], limit: int = 24) -> list[str]:
    nodes = graph.get("nodes") or []
    verse = [str(n["id"]) for n in nodes if str(n.get("kind") or "") == "verse"]
    verse.sort(key=lambda i: (-float(next((n.get("hub_score") or 0 for n in nodes if str(n.get("id")) == i), 0)), i))
    return verse[:limit]


def compute_honest_wire_metrics(
    wire_byte_len: int,
    envelope_utf8_byte_len: int,
    naive_utf8_byte_len: int,
) -> dict[str, float]:
    """LO-CG-01: payload savings vs naive JSON; governance overhead vs envelope (not compression)."""
    if naive_utf8_byte_len <= 0:
        return {
            "payload_size_ratio": 0.0,
            "payload_savings_ratio": 0.0,
            "governance_overhead_factor": 0.0,
            "envelope_to_wire_factor": 0.0,
        }
    payload_size_ratio = round(wire_byte_len / naive_utf8_byte_len, 4)
    return {
        "payload_size_ratio": payload_size_ratio,
        "payload_savings_ratio": round(1.0 - payload_size_ratio, 4),
        "governance_overhead_factor": round(envelope_utf8_byte_len / naive_utf8_byte_len, 4),
        "envelope_to_wire_factor": round(
            envelope_utf8_byte_len / wire_byte_len, 4
        )
        if wire_byte_len > 0
        else 0.0,
    }


def _encode_wire(atom_ids: list[str]) -> dict[str, Any]:
    from scripts.l1_side_channel_wire_codec import encode_adaptive_msgpack  # noqa: WPS433

    payload = {
        "schema": "mkm_lexicon_wire_v1",
        "atom_id_sequence": atom_ids,
        "atom_count": len(atom_ids),
    }
    wire_bytes, variant = encode_adaptive_msgpack(payload, zstd_min_raw_bytes=64, zstd_level=3)
    return {
        "wire_b64": base64.b64encode(wire_bytes).decode("ascii"),
        "wire_byte_len": len(wire_bytes),
        "codec_variant": "zstd_msgpack" if variant == "zstd" else "raw_msgpack",
        "atom_id_sequence": atom_ids,
        "lexicon_meta": {"source": "graph_slice_verse_nodes", "poc": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--graph-json",
        default="projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json",
    )
    parser.add_argument(
        "--verse-ids-json",
        default="",
        help="Optional seed-chain JSON with graph_rag.verse_node_ids (DF-P1-03)",
    )
    args = parser.parse_args()

    root = ROOT
    graph_path = root / args.graph_json
    if not graph_path.is_file():
        print(f"missing graph: {graph_path}", file=sys.stderr)
        return 1

    graph = _load(graph_path)
    if args.verse_ids_json.strip():
        ids_path = root / args.verse_ids_json
        if not ids_path.is_file():
            print(f"missing verse-ids json: {ids_path}", file=sys.stderr)
            return 1
        ids_doc = _load(ids_path)
        rag = ids_doc.get("graph_rag") or {}
        atom_ids = list(rag.get("verse_node_ids") or ids_doc.get("verse_node_ids") or [])
    else:
        atom_ids = _verse_atom_ids(graph)
    if len(atom_ids) < 2:
        print("insufficient verse nodes in graph slice", file=sys.stderr)
        return 1

    encode_resp = _encode_wire(atom_ids)
    from scripts.mkm_inter_agent_wire_envelope_v1 import (  # noqa: WPS433
        build_turn_envelope,
        envelope_utf8_byte_len,
        new_session_id,
    )

    session_id = new_session_id("graph-rag-poc")
    envelope = build_turn_envelope(
        encode_response=encode_resp,
        session_id=session_id,
        turn_id=1,
        from_agent="logos_graph",
        to_agent="logos_observatory",
        loss_profile="graph_rag_poc",
        routing_profile="track_c_research",
    )
    envelope_utf8 = envelope_utf8_byte_len(envelope)
    wire_byte_len = int(encode_resp.get("wire_byte_len") or 0)
    naive_payload = {"verse_node_ids": atom_ids, "graph_stats": graph.get("stats") or {}}
    naive_utf8 = len(json.dumps(naive_payload, ensure_ascii=False).encode("utf-8"))
    honest_metrics = compute_honest_wire_metrics(wire_byte_len, envelope_utf8, naive_utf8)
    governance_overhead_factor = honest_metrics["governance_overhead_factor"]

    from scripts.compute_logos_reasoning_path_v1 import compute_reasoning_path  # noqa: WPS433

    path_doc = compute_reasoning_path(graph, atom_ids[:3], max_nodes=5)
    path_nodes = list(path_doc.get("node_ids") or path_doc.get("path_node_ids") or atom_ids[:5])

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "generated_at_utc": generated_at,
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_trading_signal": True,
            "track_wall": "B_track_not_track_A",
        },
        "inputs": {
            "graph_json": str(graph_path.relative_to(root)).replace("\\", "/"),
            "graph_node_count": (graph.get("stats") or {}).get("node_count"),
            "graph_edge_count": (graph.get("stats") or {}).get("edge_count"),
        },
        "graph_rag": {
            "verse_atom_ids_sampled": len(atom_ids),
            "reasoning_path_node_ids": path_nodes,
            "path_hops": max(0, len(path_nodes) - 1),
        },
        "wire": {
            "envelope_schema": envelope.get("schema"),
            "wire_byte_len": wire_byte_len,
            "envelope_utf8_byte_len": envelope_utf8,
            "naive_json_utf8_byte_len": naive_utf8,
            "codec_variant": encode_resp.get("codec_variant"),
            "honest_metrics": honest_metrics,
            "bytes_ratio_vs_naive_json": {
                "deprecated": True,
                "value": governance_overhead_factor,
                "meaning": "governance_overhead_factor (envelope/naive); not wire payload compression",
            },
        },
        "showroom_link": {
            "product_url": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
            "trace_health_url": "https://api.jemaai.cloud/v1/logos/health",
        },
        "boundary_ack": (
            "PoC chains graph slice verse nodes to lexicon wire envelope bytes only; "
            "not 31k corpus load, not live trading, not MS FinOps claims."
        ),
    }

    out_path = root / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    out_path.write_text(payload_text, encoding="utf-8")
    showroom_poc = (
        root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
        / "showroom_logos_graph_wire_rag_poc_v1.json"
    )
    showroom_poc.parent.mkdir(parents=True, exist_ok=True)
    showroom_poc.write_text(payload_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "honest_metrics": honest_metrics,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
