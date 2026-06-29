#!/usr/bin/env python3
"""Materialize B-track lens GraphRAG router slice from seed + lens JSON [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


def build_router_slice(seed: dict[str, Any], lens: dict[str, Any] | None) -> dict[str, Any]:
    lens_id = str(seed.get("lens_id") or "unknown")
    scores = (lens or {}).get("scores") if isinstance((lens or {}).get("scores"), dict) else {}
    direction_score = float(scores.get("direction_score") or 0.0)
    paths = []
    for p in seed.get("graph_paths") or []:
        if not isinstance(p, dict):
            continue
        steps = p.get("steps") or []
        paths.append(
            {
                "path_id": p.get("path_id"),
                "steps": steps,
                "note_ko": p.get("note_ko"),
                "match_score": len(steps),
            }
        )
    node_ids = [n.get("node_id") for n in (seed.get("anchor_nodes") or []) if isinstance(n, dict)]
    return {
        "schema": "btrack_lens_graphrag_router_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lens_id": lens_id,
        "query": seed.get("query_ko"),
        "query_id": seed.get("query_id"),
        "horizon_contract": seed.get("horizon_contract"),
        "direction_score_from_lens": direction_score,
        "anchor_node_ids": node_ids,
        "paths": paths,
        "policy": {
            "no_prophecy_claim": True,
            "router_kind": "btrack_lens_slice_v1",
            "send_gate": "HOLD",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--lens-json", type=Path, default=None)
    ap.add_argument("--output-json", type=Path, required=True)
    args = ap.parse_args()

    seed = _read(args.seed)
    if not seed or seed.get("schema") != "btrack_lens_graphrag_slice_hypo_v1":
        print("Invalid seed", file=__import__("sys").stderr)
        return 2
    lens = _read(args.lens_json) if args.lens_json else None
    doc = build_router_slice(seed, lens)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "lens_id": doc["lens_id"], "paths": len(doc["paths"]), "out": str(args.output_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
