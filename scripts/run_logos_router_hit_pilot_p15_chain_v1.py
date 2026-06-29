#!/usr/bin/env python3
"""P15 router-hit pilot — GraphRAG router overlap on 200 narratives (B-track, HYPO).

Post verse-id CLOSED: enable router eval + closure refresh.
Does not rebuild bloom slice (orthogonal to resonance_cap SSOT).

Reproducible:
  py scripts/run_logos_router_hit_pilot_p15_chain_v1.py
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
CLOSURE = ROOT / "docs/final/artifacts/logos_bible_advancement_closure_v1_latest.json"
SLICE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
MIN_SAMPLES = 200
MIN_ROUTER_HIT_RATE = 1.0
MIN_BLOOM_CAP_SSOT = 128


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-cdn-purge", action="store_true")
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_adv3_graphrag_bridge_chain_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_adv3_graphrag_bridge_chain_v1.py")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    n_samples = len(bridge.get("narrative_path_samples") or [])
    if n_samples < MIN_SAMPLES:
        print(f"FAIL: narrative_path_samples={n_samples} expected >= {MIN_SAMPLES}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_narrative_path_eval_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_narrative_path_eval_v1.py (router enabled)")

    slice_before = json.loads(SLICE.read_text(encoding="utf-8")) if SLICE.is_file() else {}
    cap_before = int(slice_before.get("resonance_cap") or 0)

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_lemma_spike_drift_snapshot_v1.py", "--compare"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        print("WARN: drift compare flags (review)", file=sys.stderr)

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_bible_advancement_completion_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_bible_advancement_completion_chain_v1.py")

    if not args.skip_cdn_purge:
        proc = subprocess.run(
            [sys.executable, "scripts/purge_cloudflare_mkmlife_bloom_cache_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("WARN: CDN purge failed (review)", file=sys.stderr)

    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    if eval_doc["narrative_sample_count"] < MIN_SAMPLES:
        return 1
    if eval_doc["summary"]["sample_pass_rate"] < 1.0:
        return 1
    router_rate = eval_doc["summary"].get("router_hit_rate")
    if router_rate is None:
        print("FAIL: router_hit_rate is null (router did not run)", file=sys.stderr)
        return 1
    if router_rate < MIN_ROUTER_HIT_RATE:
        print(f"FAIL: router_hit_rate={router_rate} expected >= {MIN_ROUTER_HIT_RATE}", file=sys.stderr)
        return 1

    slice_doc = json.loads(SLICE.read_text(encoding="utf-8")) if SLICE.is_file() else {}
    cap_after = int(slice_doc.get("resonance_cap") or 0)
    if cap_before and cap_after != cap_before:
        print(
            f"FAIL: bloom resonance_cap changed {cap_before} -> {cap_after} (P15 must not rebuild bloom)",
            file=sys.stderr,
        )
        return 1
    if cap_after < MIN_BLOOM_CAP_SSOT:
        print(
            f"FAIL: bloom resonance_cap={cap_after} expected >= {MIN_BLOOM_CAP_SSOT}",
            file=sys.stderr,
        )
        return 1

    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    if closure.get("narrative_sample_count", 0) < MIN_SAMPLES:
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_router_hit_pilot_p15_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest router_hit pilot p15")

    print(
        f"narratives={n_samples} router_hit_rate={router_rate} "
        f"resonance_cap={cap_after} (unchanged) closure_narratives={closure.get('narrative_sample_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
