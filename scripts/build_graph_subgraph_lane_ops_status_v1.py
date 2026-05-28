#!/usr/bin/env python3
"""Aggregate Graph subgraph lane replay summaries into one ops status JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/graph_subgraph_lane_ops_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_status() -> dict[str, Any]:
    logos = _load(ROOT / "reports/subgraph_router_replay_summary_latest.json")
    pet = _load(ROOT / "reports/pet_companion_subgraph_replay_summary_latest.json")
    contract = _load(ROOT / "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json")
    slice_doc = _load(ROOT / "docs/final/artifacts/pet_companion_local_graph_slice_v1_latest.json")
    slots = _load(ROOT / "reports/pet_companion_memory_slots_latest.json")
    live_req = _load(ROOT / "reports/pet_companion_device_bridge_live_request_latest.json")
    live_res = _load(ROOT / "reports/pet_companion_device_bridge_live_response_latest.json")

    logos_pass = bool(logos and logos.get("pass") is True)
    pet_pass = bool(pet and pet.get("pass") is True)
    combined_pass = logos_pass and pet_pass

    return {
        "schema": "graph_subgraph_lane_ops_status_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "combined_pass": combined_pass,
        "logos_replay": {
            "present": logos is not None,
            "pass": logos_pass,
            "pass_count": (logos or {}).get("pass_count"),
            "query_count": (logos or {}).get("query_count"),
        },
        "pet_replay": {
            "present": pet is not None,
            "pass": pet_pass,
            "pass_count": (pet or {}).get("pass_count"),
            "query_count": (pet or {}).get("query_count"),
        },
        "pet_local_graph_slice": {
            "present": slice_doc is not None,
            "node_count": (slice_doc or {}).get("node_count"),
            "edge_count": (slice_doc or {}).get("edge_count"),
            "hints_applied": (slice_doc or {}).get("hints_applied"),
        },
        "pet_memory_slots": {
            "present": slots is not None,
            "events_count": (slots or {}).get("events_count"),
            "slots_count": (slots or {}).get("slots_count"),
        },
        "lane_contract_present": contract is not None,
        "device_bridge_live": {
            "request_present": live_req is not None,
            "response_present": live_res is not None,
            "response_status": (live_res or {}).get("status"),
            "bridge_slots_count": ((live_res or {}).get("input_meta_reflected") or {}).get("bridge_slots_count"),
            "hints_edges": len(
                ((live_res or {}).get("local_graph_update_hints") or {}).get("suggested_edges_to_link") or []
            ),
            "note": "Production /api/v1/pet-companion/bridge may 404 until mkmlife deploy; local dev :3105 for P5.",
        },
        "policy": {
            "no_prophecy_hit_rate_claim": True,
            "no_track_a_merge": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    doc = build_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "combined_pass": doc["combined_pass"], "out": str(out)}, ensure_ascii=False))
    return 0 if doc["combined_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
