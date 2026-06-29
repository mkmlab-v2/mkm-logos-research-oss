"""P13 verse-id pilot batch-7 narrative 176→192 contract."""

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


@pytest.fixture(scope="module")
def p13_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p13_chain_v1.py",
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


def test_narrative_one_ninety_two(p13_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 192
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_one_twelve(p13_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 112


def test_p13_eval_inter_hop_bloom(p13_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 192
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 194
    assert len(slice_doc.get("narrative_path_samples") or []) >= 192
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_cross_nt_ot") == NEW_IDS[12]
