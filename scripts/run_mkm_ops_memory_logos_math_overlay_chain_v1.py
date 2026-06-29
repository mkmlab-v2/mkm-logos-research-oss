#!/usr/bin/env python3
"""Phase 1 Logos/4D/gematria ops memory pin chain ([HYPO] / B-track).

Reproducible:
  py scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
OUT = ROOT / "reports/mkm_ops_memory_logos_math_overlay_chain_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    steps: list[dict] = []
    for script in (
        "build_mkm_ops_memory_index_v1.py",
        "build_mkm_ops_memory_logos_math_overlay_v1.py",
    ):
        proc = subprocess.run([sys.executable, f"scripts/{script}"], cwd=ROOT, check=False)
        steps.append({"step": script, "exit_code": proc.returncode})
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: {script}")

    index = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    overlays = index.get("overlays") or []
    nodes = index.get("nodes") or {}
    logos_nodes = [k for k in nodes if k.startswith("prism_ops_logos_")]
    if "logos_math_v1" not in overlays:
        print("FAIL: logos_math_v1 overlay missing", file=sys.stderr)
        return 1
    if len(logos_nodes) < 4:
        print(f"FAIL: logos nodes={len(logos_nodes)}", file=sys.stderr)
        return 1

    oracle_pack = (
        "prism_ops_logos_cosmic_anchor_bridge",
        "prism_ops_logos_router_regression_bundle",
    )
    for node_id in oracle_pack:
        if node_id not in nodes:
            print(f"FAIL: oracle pack node missing {node_id}", file=sys.stderr)
            return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_mkm_ops_memory_logos_math_overlay_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest logos math ops memory overlay")

    report = {
        "schema": "mkm_ops_memory_logos_math_overlay_chain_v1",
        "chain_pass": True,
        "research_only": True,
        "overlays": overlays,
        "logos_node_ids": sorted(logos_nodes),
        "steps": steps,
        "repro_one_shot": "py scripts/run_mkm_ops_memory_logos_math_overlay_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"chain_pass=true logos_nodes={len(logos_nodes)} overlay=logos_math_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
