#!/usr/bin/env python3
"""Oracle high-delegation bundle: mg gap close → CDN purge → P3f narrative 24.

Reproducible:
  py scripts/run_logos_oracle_infra_p3f_delegation_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
BLOOM_URL = "https://mkmlife.com/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"


def _live_narrative_count() -> int | None:
    try:
        req = urllib.request.Request(BLOOM_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode())
        return len(doc.get("narrative_path_samples") or [])
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-cdn-purge", action="store_true")
    args = parser.parse_args()

    steps = [
        [sys.executable, "scripts/run_logos_meaning_graph_gap_close_chain_v1.py", "--skip-pytest"],
    ]
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            return proc.returncode
        print(f"OK: {' '.join(cmd[1:])}")

    if not args.skip_cdn_purge:
        proc = subprocess.run(
            [sys.executable, "scripts/purge_cloudflare_mkmlife_bloom_cache_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("WARN: pre-p3f CDN purge failed", file=sys.stderr)

    p3f_cmd = [sys.executable, "scripts/run_logos_narrative_path_p3f_chain_v1.py"]
    if args.skip_pytest:
        p3f_cmd.append("--skip-pytest")
    p3f_cmd.append("--skip-router")
    if args.skip_cdn_purge:
        p3f_cmd.append("--skip-cdn-purge")
    proc = subprocess.run(p3f_cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        return proc.returncode
    print("OK: run_logos_narrative_path_p3f_chain_v1.py")

    if not args.skip_cdn_purge:
        proc = subprocess.run(
            [sys.executable, "scripts/purge_cloudflare_mkmlife_bloom_cache_v1.py"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print("WARN: post-p3f CDN purge failed", file=sys.stderr)
        else:
            time.sleep(3)
            live = _live_narrative_count()
            if live is not None:
                print(f"live_apex_narratives={live}")

    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    if bridge["summary"]["meaning_graph_hit_anchors"] < bridge["anchor_count"]:
        return 1
    if bridge["summary"]["narrative_sample_count"] < 24:
        return 1
    if bridge["summary"]["lemma_hit_anchors"] < 339:
        return 1

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_lemma_spike_drift_snapshot_v1.py", "--compare"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        print("WARN: drift compare flags (review)", file=sys.stderr)

    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_bible_advancement_completion_chain_v1.py", "--skip-pytest"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_meaning_graph_gap_close_v1.py",
                "tests/test_logos_narrative_path_p3f_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    print(
        f"delegation_ok mg={bridge['summary']['meaning_graph_hit_anchors']} "
        f"narratives={bridge['summary']['narrative_sample_count']} "
        f"lemma={bridge['summary']['lemma_hit_anchors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
