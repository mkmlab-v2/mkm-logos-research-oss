#!/usr/bin/env python3
"""Phase 4 [HYPO]: WebGPU LOD policy artifact for magic orb graph bloom."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_webgpu_lod_policy_v1_latest.json"
MKMLIFE_OUT = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_webgpu_lod_policy_v1.json"

SCHEMA = "magic_orb_webgpu_lod_policy_v1"
GRAPH_BLOOM_DISPLAY_HUB_CAP = 12
GRAPH_BLOOM_NODE_CAP = 64

TIERS = [
    {
        "tier": "canvas_compact",
        "backend": "canvas2d",
        "display_hub_cap": GRAPH_BLOOM_DISPLAY_HUB_CAP,
        "render_all_nodes": False,
        "render_non_hub_edges": False,
        "min_node_count": 0,
        "max_node_count": 24,
    },
    {
        "tier": "canvas_standard",
        "backend": "canvas2d",
        "display_hub_cap": 24,
        "render_all_nodes": False,
        "render_non_hub_edges": True,
        "min_node_count": 25,
        "max_node_count": 40,
    },
    {
        "tier": "canvas_dense",
        "backend": "canvas2d",
        "display_hub_cap": 32,
        "render_all_nodes": True,
        "render_non_hub_edges": True,
        "min_node_count": 41,
        "max_node_count": 47,
    },
    {
        "tier": "webgpu_hypo",
        "backend": "webgpu_hypo",
        "display_hub_cap": GRAPH_BLOOM_NODE_CAP,
        "render_all_nodes": True,
        "render_non_hub_edges": True,
        "min_node_count": 48,
        "max_node_count": GRAPH_BLOOM_NODE_CAP,
        "requires_webgpu": True,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_tier(node_count: int, *, webgpu_available: bool = False, quality: str = "high") -> str:
    if quality == "low" or node_count <= 24:
        return "canvas_compact"
    if quality == "medium" or node_count <= 40:
        return "canvas_standard"
    if webgpu_available and node_count >= 48 and quality == "high":
        return "webgpu_hypo"
    return "canvas_dense"


def build_policy() -> dict:
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "disclaimer_ko": "WebGPU 경로는 [HYPO] 관측 쇼룸용입니다. 실매매·Track A·의료 근거 아님.",
        "tiers": TIERS,
        "resolve_rules": {
            "quality_low_max_nodes": 24,
            "quality_medium_max_nodes": 40,
            "webgpu_hypo_min_nodes": 48,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build magic_orb_webgpu_lod_policy_v1 JSON.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sync-mkmlife", action="store_true")
    args = ap.parse_args()

    doc = build_policy()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.sync_mkmlife:
        MKMLIFE_OUT.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "tiers": len(doc["tiers"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
