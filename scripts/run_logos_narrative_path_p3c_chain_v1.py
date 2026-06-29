#!/usr/bin/env python3
"""P3c — Narrative 8→12 curation + lemma/inter-hop re-eval chain (B-track, HYPO).

Reproducible:
  py scripts/run_logos_narrative_path_p3c_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
INTER_HOP = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-router", action="store_true")
    args = parser.parse_args()

    steps: list[list[str]] = [
        [sys.executable, "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py"],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: {cmd[1]}")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    n_samples = len(bridge.get("narrative_path_samples") or [])
    if n_samples < 12:
        print(f"FAIL: narrative_path_samples={n_samples} expected >= 12", file=sys.stderr)
        return 1

    eval_cmd = [sys.executable, "scripts/build_logos_narrative_path_eval_v1.py"]
    if args.skip_router:
        eval_cmd.append("--skip-router")
    proc = subprocess.run(eval_cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_narrative_path_eval_v1.py")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bloom_slice_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_cosmic_anchor_graph_bloom_slice_v1.py")

    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_narrative_inter_hop_bridge_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_narrative_inter_hop_bridge_chain_v1.py")

    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    if eval_doc["narrative_sample_count"] < 12:
        return 1
    if eval_doc["summary"]["path_ok_rate"] < 1.0:
        return 1
    if eval_doc["summary"]["sample_pass_rate"] < 1.0:
        return 1

    overlap_doc = json.loads(OVERLAP.read_text(encoding="utf-8"))
    if overlap_doc["summary"]["hop_lemma_edge_hit_rate"] < 1.0:
        return 1
    if overlap_doc["summary"]["curated_bridge_pair_rate"] < 1.0:
        return 1

    inter_doc = json.loads(INTER_HOP.read_text(encoding="utf-8"))
    if inter_doc["summary"]["inter_hop_pair_count"] < 14:
        print("FAIL: inter_hop_pair_count < 14", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_narrative_path_p3c_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest p3c narrative")

    print(f"narrative_samples={n_samples} inter_hop_pairs={inter_doc['summary']['inter_hop_pair_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
