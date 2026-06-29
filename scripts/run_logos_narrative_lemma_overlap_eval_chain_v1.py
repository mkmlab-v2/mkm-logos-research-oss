#!/usr/bin/env python3
"""Narrative 8-path × lemma overlap eval chain (B-track, HYPO).

Reproducible:
  py scripts/run_logos_narrative_lemma_overlap_eval_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
BIDIRECTIONAL = ROOT / "reports/logos_bidirectional_anchor_index_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-bridge-refresh", action="store_true")
    args = parser.parse_args()

    if not args.skip_bridge_refresh:
        proc = subprocess.run(
            [sys.executable, "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("FAIL: run_logos_adv3_graphrag_bridge_chain_v1.py", file=sys.stderr)
            return proc.returncode
        print("OK: run_logos_adv3_graphrag_bridge_chain_v1.py")

    if not BIDIRECTIONAL.is_file():
        proc = subprocess.run(
            [sys.executable, "scripts/build_logos_bidirectional_anchor_index_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("FAIL: build_logos_bidirectional_anchor_index_v1.py", file=sys.stderr)
            return proc.returncode
        print("OK: build_logos_bidirectional_anchor_index_v1.py")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    n_samples = len(bridge.get("narrative_path_samples") or [])
    if n_samples < 8:
        print(f"FAIL: narrative_path_samples={n_samples} expected >= 8", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_narrative_lemma_overlap_eval_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_narrative_lemma_overlap_eval_v1.py")

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_narrative_lemma_overlap_eval_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest lemma overlap eval")

    if not EVAL.is_file():
        return 1
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    if doc["narrative_sample_count"] < 8:
        return 1
    if doc["summary"]["hop_bidirectional_atom_hit_rate"] < 1.0:
        print("FAIL: hop_bidirectional_atom_hit_rate < 1.0", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
