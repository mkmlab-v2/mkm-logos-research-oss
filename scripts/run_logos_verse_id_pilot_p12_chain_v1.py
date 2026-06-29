#!/usr/bin/env python3
"""P12 verse-id pilot batch-6 — Narrative 160→176 + bloom + inter-hop (B-track, HYPO).

Matt/Luke/Genesis/Leviticus/Jeremiah/Hebrews cluster (+16 paths).

Reproducible:
  py scripts/run_logos_verse_id_pilot_p12_chain_v1.py
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
MIN_SAMPLES = 176
MIN_INTER_HOP_PAIRS = 178
MIN_VID_TOTAL = 96

PILOT_PREFIX = "vid_"
NEW_SAMPLE_IDS = (
    "vid_matt_7_19_to_matt_8_8_faith",
    "vid_luke_5_23_to_luke_5_24_paralytic",
    "vid_luke_7_40_to_luke_7_43_forgiveness",
    "vid_luke_9_20_to_luke_9_49_messiah",
    "vid_gen_2_9_to_gen_2_19_eden",
    "vid_gen_3_12_to_gen_3_23_fall",
    "vid_gen_4_11_to_gen_4_23_cain",
    "vid_gen_6_7_to_gen_8_2_flood",
    "vid_gen_21_15_to_gen_24_55_isaac",
    "vid_gen_27_31_to_gen_27_39_jacob",
    "vid_gen_29_14_to_gen_37_14_joseph",
    "vid_gen_40_12_to_gen_41_14_dream",
    "vid_gen_49_10_to_gen_49_28_blessing",
    "vid_lev_11_16_to_lev_11_29_clean",
    "vid_jer_8_2_to_jer_16_4_judgment",
    "vid_heb_9_4_to_heb_9_13_blood",
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
        print(f"FAIL: missing batch-6 samples {missing}", file=sys.stderr)
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
            [sys.executable, "-m", "pytest", "tests/test_logos_verse_id_pilot_p12_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest verse_id pilot p12")

    print(
        f"narrative_samples={n_samples} verse_id_pilot={vid_count} "
        f"inter_hop_pairs={inter_doc['summary']['inter_hop_pair_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
