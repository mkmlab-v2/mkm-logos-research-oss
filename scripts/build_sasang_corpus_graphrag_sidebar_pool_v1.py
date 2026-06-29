#!/usr/bin/env python3
"""Build sasang GraphRAG sidebar candidate pool from interpretive bundle + tail router [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
DEFAULT_ROUTER = ROOT / "reports/btrack_lens_graphrag_sasang_kospi_tail_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/sasang_corpus_graphrag_sidebar_pool_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/sasang_corpus_graphrag_sidebar_pool_v1_latest.json"

SASANG_AXIS_IDS = frozenset({"sasang_lens_core", "market_sasang_lens"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _axis_pool_entries(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sec in bundle.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        aid = str(sec.get("axis_id") or "")
        if aid not in SASANG_AXIS_IDS:
            continue
        depth = str(sec.get("interpretive_depth_ko") or sec.get("summary_ko") or "")[:240]
        refs = sec.get("evidence_refs") or []
        ref0 = refs[0] if refs and isinstance(refs[0], dict) else {}
        out.append(
            {
                "hit_type": "sasang_axis_depth",
                "source_rail": "sasang_interpretive_insight_bundle",
                "axis_id": aid,
                "title_ko": sec.get("title_ko"),
                "summary": depth,
                "anchor_ref": ref0.get("ref"),
                "match_reason": "bundle_axis_sidebar_pool",
            }
        )
    return out


def _router_pool_entries(router: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not router:
        return []
    out: list[dict[str, Any]] = []
    for i, p in enumerate(router.get("paths") or [], start=1):
        if not isinstance(p, dict):
            continue
        out.append(
            {
                "hit_type": "graphrag_path",
                "source_rail": "btrack_lens_graphrag_router",
                "path_id": p.get("path_id"),
                "steps": (p.get("steps") or [])[:5],
                "summary": str(p.get("note_ko") or "")[:200],
                "match_score": p.get("match_score"),
                "rank": i,
            }
        )
    anchors = router.get("anchor_node_ids") or []
    if isinstance(anchors, list):
        for j, node_id in enumerate(anchors[:3], start=1):
            out.append(
                {
                    "hit_type": "anchor_node",
                    "source_rail": "btrack_lens_graphrag_router",
                    "node_id": node_id,
                    "summary": f"anchor::{node_id}",
                    "rank": len(out) + 1,
                }
            )
    return out


def build_pool(
    *,
    bundle: dict[str, Any],
    router: dict[str, Any] | None,
) -> dict[str, Any]:
    axis_entries = _axis_pool_entries(bundle)
    router_entries = _router_pool_entries(router)
    return {
        "schema": "sasang_corpus_graphrag_sidebar_pool_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "prophecy_vote": "none",
        "decision_authority": "human_only",
        "policy": {
            "opt_in_only": True,
            "wires_to_scoring_core": False,
            "max_anchor_ids": 3,
        },
        "candidate_pools": {
            "sasang_axis_depth": axis_entries,
            "graphrag_paths": router_entries,
        },
        "pool_counts": {
            "sasang_axis_depth": len(axis_entries),
            "graphrag_paths": len(router_entries),
            "total": len(axis_entries) + len(router_entries),
        },
        "pointers": {
            "bundle": str(DEFAULT_BUNDLE),
            "router": str(DEFAULT_ROUTER),
        },
        "reproduce": "py scripts/build_sasang_corpus_graphrag_sidebar_pool_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args(argv)

    bundle = _read(args.bundle_json)
    if not bundle:
        print(f"Missing bundle: {args.bundle_json}", file=sys.stderr)
        return 2

    router = _read(args.router_json)
    doc = build_pool(bundle=bundle, router=router)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "total": doc["pool_counts"]["total"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
