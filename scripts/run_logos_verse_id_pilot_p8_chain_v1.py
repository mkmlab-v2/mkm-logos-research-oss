#!/usr/bin/env python3
"""P8 verse-id pilot batch-2 — Narrative 96→112 + bloom + inter-hop (B-track, HYPO).

Matthew/Luke/Revelation + Genesis cluster (+16 paths).

Reproducible:
  py scripts/run_logos_verse_id_pilot_p8_chain_v1.py
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
MIN_SAMPLES = 112
MIN_INTER_HOP_PAIRS = 114
MIN_VID_TOTAL = 32

PILOT_PREFIX = "vid_"
NEW_SAMPLE_IDS = (
    "vid_matt_3_10_to_matt_3_15_baptism",
    "vid_matt_4_4_to_matt_5_22_temptation_ethics",
    "vid_matt_11_4_to_matt_11_25_messenger",
    "vid_matt_12_39_to_matt_12_48_sign_family",
    "vid_matt_14_28_to_matt_16_16_faith_confession",
    "vid_matt_17_4_to_matt_17_17_transfiguration",
    "vid_luke_1_19_to_luke_1_35_annunciation",
    "vid_luke_4_8_to_luke_4_12_temptation_word",
    "vid_luke_10_27_to_luke_10_42_love_mary",
    "vid_luke_22_36_to_luke_22_51_sword_ear",
    "vid_luke_23_3_to_luke_23_41_cross_penitent",
    "vid_rev_6_13_to_rev_6_14_seal_cosmos",
    "vid_rev_11_1_to_rev_11_6_two_witnesses",
    "vid_rev_12_15_to_rev_14_18_dragon_harvest",
    "vid_gen_13_14_to_gen_14_19_abram_call",
    "vid_gen_18_17_to_gen_19_14_sodom_warning",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-router", action="store_true")
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
    samples = bridge.get("narrative_path_samples") or []
    n_samples = len(samples)
    sample_ids = {s["sample_id"] for s in samples}
    vid_count = sum(1 for s in samples if str(s.get("sample_id") or "").startswith(PILOT_PREFIX))

    if n_samples < MIN_SAMPLES:
        print(f"FAIL: narrative_path_samples={n_samples} expected >= {MIN_SAMPLES}", file=sys.stderr)
        return 1
    if vid_count < MIN_VID_TOTAL:
        print(f"FAIL: verse_id_pilot_total={vid_count} expected >= {MIN_VID_TOTAL}", file=sys.stderr)
        return 1
    missing = [sid for sid in NEW_SAMPLE_IDS if sid not in sample_ids]
    if missing:
        print(f"FAIL: missing batch-2 samples {missing}", file=sys.stderr)
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

    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    if eval_doc["narrative_sample_count"] < MIN_SAMPLES:
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
    if inter_doc["summary"]["inter_hop_pair_count"] < MIN_INTER_HOP_PAIRS:
        print(
            f"FAIL: inter_hop_pair_count={inter_doc['summary']['inter_hop_pair_count']} "
            f"expected >= {MIN_INTER_HOP_PAIRS}",
            file=sys.stderr,
        )
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_verse_id_pilot_p8_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest verse_id pilot p8")

    print(
        f"narrative_samples={n_samples} verse_id_pilot={vid_count} "
        f"inter_hop_pairs={inter_doc['summary']['inter_hop_pair_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
