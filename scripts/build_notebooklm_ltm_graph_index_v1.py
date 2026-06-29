#!/usr/bin/env python3
"""Build compact LTM graph index for NotebookLM ingest (not full graph JSON).

  py scripts/build_notebooklm_ltm_graph_index_v1.py
  py scripts/build_notebooklm_ltm_graph_index_v1.py --out docs/final/artifacts/notebooklm_ltm_graph_index_v1.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = SCRIPT_ROOT / "storage" / "meta" / "mkm_long_term_memory_graph_v1.json"
DEFAULT_OUT = SCRIPT_ROOT / "docs" / "final" / "artifacts" / "notebooklm_ltm_graph_index_v1.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_index_markdown(graph: dict) -> str:
    concepts = graph.get("concepts") or {}
    edges = graph.get("edges") or []
    rows: list[tuple[int, str, str, str, str]] = []
    for cid, c in concepts.items():
        label = str(c.get("label_ko") or cid)
        essence = str(c.get("essence") or "").replace("\n", " ")[:120]
        lane = str(c.get("lane_hint") or "-")
        priority = int(c.get("priority") or 0)
        rows.append((priority, cid, label, lane, essence))
    rows.sort(key=lambda r: (-r[0], r[1]))

    lines = [
        "# MKM LTM Graph — NotebookLM concept index (compact)",
        "",
        f"**Generated:** {utc_now()}  ",
        "**Track:** B · `[HYPO]` · `research_only`  ",
        "**Purpose:** NL 지휘부 Read-only routing index — not implementation SSOT.",
        "",
        f"- **concept_count:** {len(concepts)}",
        f"- **edge_count:** {len(edges)}",
        f"- **full_graph_path:** `storage/meta/mkm_long_term_memory_graph_v1.json`",
        "",
        "| priority | concept_id | lane | label_ko | essence (trim) |",
        "|---:|---|---|---|---|",
    ]
    for priority, cid, label, lane, essence in rows:
        safe_label = label.replace("|", "/")
        safe_ess = essence.replace("|", "/")
        lines.append(f"| {priority} | `{cid}` | {lane} | {safe_label} | {safe_ess} |")

    lines.extend(
        [
            "",
            "## Lane resume packs (local inject)",
            "",
            "| lane | node_ids (LANE_OPS_PACKS) |",
            "|---|---|",
            "| ms | prism_ops_mission_log_board, prism_ops_central_checkpoint, prism_ops_lane_ms |",
            "| oracle | prism_ops_mission_log_board, prism_ops_central_checkpoint, prism_ops_lane_oracle |",
            "| infra | prism_ops_mission_log_board, prism_ops_central_checkpoint, prism_ops_lane_infra |",
            "| web_ops | prism_ops_mission_log_board, prism_ops_central_checkpoint, prism_ops_web_ops_regime_gate |",
            "",
            "**Fact-Lock:** 구현·통과는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + 스크립트 exit code만.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.graph.is_file():
        print(f"FAIL: graph missing: {args.graph}", file=sys.stderr)
        return 1

    graph = json.loads(args.graph.read_text(encoding="utf-8-sig"))
    md = build_index_markdown(graph)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"WROTE: {args.out} ({len(graph.get('concepts') or {})} concepts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
