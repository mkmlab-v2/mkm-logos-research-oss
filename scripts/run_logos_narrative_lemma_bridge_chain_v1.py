#!/usr/bin/env python3
"""Narrative lemma bridge chain — merge bi-atoms, rebuild graph bridge, re-eval overlap.

Reproducible:
  py scripts/run_logos_narrative_lemma_bridge_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
REPORT = ROOT / "docs/final/artifacts/logos_narrative_lemma_bridge_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_adv3_graphrag_bridge_chain_v1.py")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_narrative_lemma_bridge_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_narrative_lemma_bridge_v1.py")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_cosmic_anchor_graph_bridge_v1.py")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    lemma_hits = bridge.get("summary", {}).get("lemma_hit_anchors", 0)
    if lemma_hits < 27:
        print(f"FAIL: lemma_hit_anchors regressed to {lemma_hits}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_lemma_overlap_eval_chain_v1.py",
            "--skip-pytest",
            "--skip-bridge-refresh",
        ],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_narrative_lemma_overlap_eval_chain_v1.py")

    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    if overlap["summary"]["hop_lemma_edge_hit_rate"] < 1.0:
        print("FAIL: hop_lemma_edge_hit_rate < 1.0 after narrative bridge", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_narrative_lemma_bridge_v1.py",
                "tests/test_logos_narrative_lemma_overlap_eval_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest narrative lemma bridge")

    if not REPORT.is_file():
        return 1
    print(f"lemma_hit_anchors={lemma_hits} hop_lemma_edge_hit_rate=1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
