#!/usr/bin/env python3
"""DF-P1-03: Seed chain verse_ids → wire envelope honest profile (one command)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "logos_graph_wire_profile_v1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed-chain-json",
        default="docs/final/artifacts/logos_graph_seed_chain_v1_latest.json",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_graph_wire_profile_v1_latest.json",
    )
    parser.add_argument(
        "--poc-json",
        default="docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json",
    )
    args = parser.parse_args()

    py = sys.executable
    steps = [
        [py, str(ROOT / "scripts/run_logos_graph_seed_chain_v1.py")],
        [
            py,
            str(ROOT / "scripts/build_mkm_graph_wire_rag_poc_v1.py"),
            "--verse-ids-json",
            args.seed_chain_json,
        ],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            return proc.returncode

    seed_path = ROOT / args.seed_chain_json
    poc_path = ROOT / args.poc_json
    if not seed_path.is_file() or not poc_path.is_file():
        print("missing seed or poc artifact", file=sys.stderr)
        return 1

    seed_doc = json.loads(seed_path.read_text(encoding="utf-8"))
    poc_doc = json.loads(poc_path.read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "seed_chain_path": str(seed_path.relative_to(ROOT)).replace("\\", "/"),
        "poc_path": str(poc_path.relative_to(ROOT)).replace("\\", "/"),
        "verse_count": (seed_doc.get("graph_rag") or {}).get("verse_count"),
        "honest_metrics": (poc_doc.get("wire") or {}).get("honest_metrics"),
        "boundary_ack": "Chained seed BFS + wire PoC; not MS FinOps or Track A.",
    }
    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
