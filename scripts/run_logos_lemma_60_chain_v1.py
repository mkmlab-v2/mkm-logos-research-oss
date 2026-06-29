#!/usr/bin/env python3
"""Lemma-60/P5/P6 spike chain — baseline → spike loop → drift check (HYPO).

Reproducible:
  py scripts/run_logos_lemma_60_chain_v1.py
  py scripts/run_logos_lemma_60_chain_v1.py --target 100
  py scripts/run_logos_lemma_60_chain_v1.py --target 200
  py scripts/run_logos_lemma_60_chain_v1.py --target 300
  py scripts/run_logos_lemma_60_chain_v1.py --target 339
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
SPIKE = ROOT / "docs/final/artifacts/logos_lemma_anchor_spike_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=60)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--skip-bridge-refresh", action="store_true")
    args = parser.parse_args()

    if not args.skip_baseline:
        proc = subprocess.run(
            [sys.executable, "scripts/build_logos_lemma_spike_drift_snapshot_v1.py", "--write-baseline"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: drift baseline")

    bridge_before = json.loads(BRIDGE.read_text(encoding="utf-8"))
    before_hits = int((bridge_before.get("summary") or {}).get("lemma_hit_anchors") or 0)

    if not args.skip_bridge_refresh:
        proc = subprocess.run(
            [sys.executable, "scripts/run_logos_narrative_lemma_bridge_chain_v1.py", "--skip-pytest"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        proc = subprocess.run(
            [sys.executable, "scripts/build_logos_narrative_inter_hop_bridge_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: narrative+inter-hop lemma refresh")

    for attempt in range(6):
        bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
        current = int((bridge.get("summary") or {}).get("lemma_hit_anchors") or 0)
        if current >= args.target:
            break
        proc = subprocess.run(
            [sys.executable, "scripts/build_logos_lemma_anchor_spike_v1.py", "--target", str(args.target)],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        proc = subprocess.run(
            [sys.executable, "scripts/build_logos_cosmic_anchor_graph_bridge_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        after = int(json.loads(BRIDGE.read_text(encoding="utf-8"))["summary"]["lemma_hit_anchors"])
        print(f"OK: spike attempt {attempt + 1} lemma_hit_anchors={after}")
        if after >= args.target:
            break
        if after <= current:
            print(f"FAIL: spike plateau at {after} target={args.target}", file=sys.stderr)
            return 1

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    after_hits = int((bridge.get("summary") or {}).get("lemma_hit_anchors") or 0)
    if after_hits < args.target:
        print(f"FAIL: lemma_hit_anchors={after_hits} target={args.target}", file=sys.stderr)
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
    print("OK: lemma overlap re-eval")

    if args.target >= 100:
        if args.target >= 300:
            narrative_chain = "scripts/run_logos_narrative_path_p3e_chain_v1.py"
        elif args.target >= 200:
            narrative_chain = "scripts/run_logos_narrative_path_p3d_chain_v1.py"
        else:
            narrative_chain = "scripts/run_logos_narrative_path_p3c_chain_v1.py"
        proc = subprocess.run(
            [sys.executable, narrative_chain, "--skip-pytest", "--skip-router"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: {narrative_chain}")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_lemma_spike_drift_snapshot_v1.py", "--compare"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        print("WARN: drift check flags present", file=sys.stderr)
    else:
        print("OK: drift check pass")

    pytest_targets = ["tests/test_logos_lemma_60_chain_v1.py"]
    if args.target >= 100:
        pytest_targets.append("tests/test_logos_lemma_100_chain_v1.py")
    if args.target >= 200:
        pytest_targets.append("tests/test_logos_lemma_200_chain_v1.py")
    if args.target >= 300:
        pytest_targets.append("tests/test_logos_lemma_300_chain_v1.py")
    if args.target >= 339:
        pytest_targets.append("tests/test_logos_lemma_339_chain_v1.py")
    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *pytest_targets, "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest lemma spike")

    spike_doc = json.loads(SPIKE.read_text(encoding="utf-8"))
    print(
        f"lemma_hit_anchors {before_hits} -> {after_hits} "
        f"candidates={spike_doc.get('candidate_anchor_count')} target={args.target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
