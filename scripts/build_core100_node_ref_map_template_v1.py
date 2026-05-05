#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 89
# Purpose: Build unresolved node-to-verse mapping template for core100 overlap calibration.
# Keywords: core100, node map, template, verse mapping
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build core100 node->verse ref map template.")
    ap.add_argument("--nodes-jsonl", default="docs/final/artifacts/global_atom_network_core100_nodes_latest.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    args = ap.parse_args()

    nodes_path = resolve(args.nodes_jsonl)
    out_path = resolve(args.output_json)
    if not nodes_path.is_file():
        raise SystemExit(f"missing nodes jsonl: {nodes_path}")

    rows: list[dict[str, Any]] = []
    for line in nodes_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        obj = json.loads(s)
        if not isinstance(obj, dict):
            continue
        node_id = str(obj.get("node_id", "")).strip()
        if not node_id:
            continue
        rows.append(
            {
                "node_id": node_id,
                "verse_ref": "",
                "status": "unresolved",
                "note": "Fill with canonical verse reference like Gen.2.9",
            }
        )

    out = {
        "schema": "core100_node_ref_map_template_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
