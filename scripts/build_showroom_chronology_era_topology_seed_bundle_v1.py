#!/usr/bin/env python3
"""Build chronology era verse seed bundle for showroom meaning topology slice."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.showroom_chronology_era_topology_seed_v1 import (  # noqa: E402
    build_chronology_era_seed_bundle,
)

DEFAULT_CHRONO = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
OUT_ART = ROOT / "docs/final/artifacts/showroom_chronology_era_topology_seed_bundle_v1_latest.json"


def _iter_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_nodes_index(path: Path) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in _iter_jsonl(path):
        nid = row.get("node_id")
        if nid:
            index[str(nid)] = row
    return index


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONO)
    ap.add_argument("--graph-nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--graph-edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out-artifact", type=Path, default=OUT_ART)
    args = ap.parse_args()

    chrono = json.loads(args.chronology_json.read_text(encoding="utf-8"))
    nodes_index = _load_nodes_index(args.graph_nodes_jsonl) if args.graph_nodes_jsonl.is_file() else {}
    edges_index = _iter_jsonl(args.graph_edges_jsonl) if args.graph_edges_jsonl.is_file() else []

    bundle = build_chronology_era_seed_bundle(chrono, nodes_index=nodes_index, edges_index=edges_index)
    bundle["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle["research_only"] = True
    bundle["hypothesis_tier"] = "B"

    text = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_artifact),
                "node_ids": len(bundle.get("node_ids") or []),
                "edges": len(bundle.get("edges") or []),
                "stub_verse_count": bundle.get("stub_verse_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
