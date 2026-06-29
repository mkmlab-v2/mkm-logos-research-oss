#!/usr/bin/env python3
"""Close meaning_graph gap for numbered-book verse nodes (HYPO, B-track).

Reproducible:
  py scripts/run_logos_meaning_graph_gap_close_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
MISSING_STEMS = (
    "2chr_6_25",
    "2sam_14_7",
    "cross",
    "flood_judgment",
    "milk",
    "shelter",
    "stronghold",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, "scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_cosmic_anchor_graph_bridge_v1.py")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    mg_hits = int(bridge["summary"]["meaning_graph_hit_anchors"])
    anchor_count = int(bridge["anchor_count"])
    if mg_hits < anchor_count:
        missing = [
            r["file_stem"]
            for r in bridge["per_anchor"]
            if int(r.get("meaning_graph_edge_count") or 0) == 0
        ]
        print(f"FAIL: meaning_graph_hit_anchors={mg_hits} missing={missing}", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_meaning_graph_gap_close_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest meaning_graph gap close")

    print(f"meaning_graph_hit_anchors={mg_hits}/{anchor_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
