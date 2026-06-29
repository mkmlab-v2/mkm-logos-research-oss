#!/usr/bin/env python3
"""P13 verse-id pilot batch-7 — Narrative 176→192 + bloom + inter-hop (B-track, HYPO).

Genesis cluster + cross-book OT/NT pilots (+16 paths).

Reproducible:
  py scripts/run_logos_verse_id_pilot_p13_chain_v1.py
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
MIN_SAMPLES = 192
MIN_INTER_HOP_PAIRS = 194
MIN_VID_TOTAL = 112

PILOT_PREFIX = "vid_"
NEW_SAMPLE_IDS = (
    "vid_gen_2_20_to_gen_2_22_river",
    "vid_gen_3_17_to_gen_4_19_curse",
    "vid_gen_5_29_to_gen_7_7_lineage",
    "vid_gen_7_17_to_gen_7_18_ark",
    "vid_gen_8_8_to_gen_8_16_dove",
    "vid_gen_24_40_to_gen_24_56_rebekah",
    "vid_gen_25_30_to_gen_26_32_esau",
    "vid_gen_27_32_to_gen_27_33_blessing",
    "vid_gen_29_25_to_gen_30_38_rachel",
    "vid_gen_33_5_to_gen_33_15_esau_meet",
    "vid_gen_37_21_to_gen_37_32_joseph_pit",
    "vid_gen_38_17_to_gen_38_20_tamar",
    "vid_jhn_19_33_to_heb_9_5_passion",
    "vid_luke_9_41_to_acts_8_24_gospel_mission",
    "vid_lev_11_22_to_2sam_14_7_clean_king",
    "vid_2chr_6_25_to_hos_2_20_temple_covenant",
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
        print(f"FAIL: missing batch-7 samples {missing}", file=sys.stderr)
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
            [sys.executable, "-m", "pytest", "tests/test_logos_verse_id_pilot_p13_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest verse_id pilot p13")

    print(
        f"narrative_samples={n_samples} verse_id_pilot={vid_count} "
        f"inter_hop_pairs={inter_doc['summary']['inter_hop_pair_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
