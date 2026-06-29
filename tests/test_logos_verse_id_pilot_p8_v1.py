"""P8 verse-id pilot batch-2 narrative 96→112 contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
SLICE = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
INTER = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"

NEW_IDS = (
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


@pytest.fixture(scope="module")
def p8_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p8_chain_v1.py",
            "--skip-pytest",
            "--skip-router",
            "--skip-cdn-purge",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_narrative_one_twelve(p8_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 112
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_thirty_two(p8_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 32


def test_p8_eval_inter_hop_bloom(p8_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 112
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 114
    assert len(slice_doc.get("narrative_path_samples") or []) >= 112
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_rev_witnesses") == NEW_IDS[12]
