#!/usr/bin/env python3
"""P10 resonance_cap 64→72 bloom slice deepen (B-track, HYPO).

Oracle lane label P20; narrative count frozen at 200; inter-hop not re-run.

Reproducible:
  py scripts/run_logos_resonance_cap_p10_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
SLICE_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
TARGET_CAP = 72
MIN_NARRATIVES = 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-cdn-purge", action="store_true")
    parser.add_argument("--resonance-cap", type=int, default=TARGET_CAP)
    args = parser.parse_args()

    if args.resonance_cap < TARGET_CAP:
        print(f"FAIL: resonance_cap={args.resonance_cap} expected >= {TARGET_CAP}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_logos_cosmic_anchor_graph_bloom_slice_v1.py",
            "--resonance-cap",
            str(args.resonance_cap),
        ],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_cosmic_anchor_graph_bloom_slice_v1.py")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    n_samples = len(bridge.get("narrative_path_samples") or [])
    if n_samples < MIN_NARRATIVES:
        print(f"FAIL: narrative_path_samples={n_samples} expected >= {MIN_NARRATIVES}", file=sys.stderr)
        return 1

    slice_doc = json.loads(SLICE_ART.read_text(encoding="utf-8"))
    cap = int(slice_doc.get("resonance_cap") or 0)
    top_n = len(slice_doc.get("resonance_edges_top") or [])
    if cap < TARGET_CAP or top_n < TARGET_CAP:
        print(f"FAIL: resonance_cap={cap} top={top_n} expected >= {TARGET_CAP}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_lemma_spike_drift_snapshot_v1.py", "--compare"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        print("WARN: drift compare flags (review)", file=sys.stderr)

    if not args.skip_cdn_purge:
        proc = subprocess.run(
            [sys.executable, "scripts/purge_cloudflare_mkmlife_bloom_cache_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("WARN: CDN purge failed (review)", file=sys.stderr)

    if OVERLAP.is_file():
        overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
        if overlap["summary"]["hop_lemma_edge_hit_rate"] < 1.0:
            print("FAIL: hop_lemma_edge_hit_rate < 1.0", file=sys.stderr)
            return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_resonance_cap_p10_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest resonance_cap p10")

    print(
        f"narratives={n_samples} resonance_cap={cap} resonance_top={top_n} "
        f"lemma_hits={bridge['summary']['lemma_hit_anchors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
