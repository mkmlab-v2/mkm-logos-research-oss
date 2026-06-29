#!/usr/bin/env python3
"""Inter-hop narrative bridge chain — curate bridges, merge lemma edges, re-eval.

Reproducible:
  py scripts/run_logos_narrative_inter_hop_bridge_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    steps = [
        [sys.executable, "scripts/run_logos_narrative_lemma_bridge_chain_v1.py", "--skip-pytest"],
        [sys.executable, "scripts/build_logos_narrative_inter_hop_bridge_v1.py"],
        [
            sys.executable,
            "scripts/run_logos_narrative_lemma_overlap_eval_chain_v1.py",
            "--skip-pytest",
            "--skip-bridge-refresh",
        ],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {' '.join(cmd[1:])} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {cmd[1]}")

    bridge_doc = json.loads(BRIDGE.read_text(encoding="utf-8"))
    if bridge_doc["summary"]["bridge_pair_rate"] < 1.0:
        return 1

    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    summary = overlap.get("summary") or {}
    if summary.get("curated_bridge_pair_rate", 0) < 1.0:
        print("FAIL: curated_bridge_pair_rate < 1.0", file=sys.stderr)
        return 1
    if (summary.get("mean_inter_hop_bridge_lemma_jaccard") or 0) < 0.5:
        print("FAIL: mean_inter_hop_bridge_lemma_jaccard < 0.5", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_narrative_inter_hop_bridge_v1.py",
                "tests/test_logos_narrative_lemma_overlap_eval_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest inter-hop bridge")

    print(
        "curated_bridge_pair_rate=1.0 "
        f"mean_inter_hop_bridge_lemma_jaccard={summary.get('mean_inter_hop_bridge_lemma_jaccard')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
