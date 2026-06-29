#!/usr/bin/env python3
"""ADV-3 GraphRAG bridge chain — cosmic anchor graph + evidence pack + router smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
EVIDENCE = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
ROUTER = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-router", action="store_true")
    parser.add_argument("--skip-evidence", action="store_true")
    args = parser.parse_args()

    steps: list[list[str]] = [
        [sys.executable, "scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py"],
        [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"],
    ]
    if not args.skip_evidence:
        steps.append(
            [sys.executable, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]
        )
    if not args.skip_router:
        steps.append(
            [
                sys.executable,
                "scripts/run_logos_subgraph_graphrag_router_v1.py",
                "--query",
                "[HYPO] 빛이 이사야 고난에서 요한복음으로 이어지는 서사 경로는 어디인가",
            ]
        )

    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {' '.join(cmd[1:])} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {cmd[1]}")

    if not BRIDGE.is_file():
        return 1
    doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    if doc.get("anchor_count", 0) < 300:
        print("FAIL: bridge anchor_count < 300", file=sys.stderr)
        return 1
    if not args.skip_evidence and not EVIDENCE.is_file():
        return 1
    if not args.skip_router and not ROUTER.is_file():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
