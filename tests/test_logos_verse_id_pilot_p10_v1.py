"""P10 verse-id pilot batch-4 narrative 128→144 contract."""

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
    "vid_matt_15_15_to_matt_15_26_tradition",
    "vid_matt_17_11_to_matt_17_12_elijah",
    "vid_matt_19_4_to_matt_19_27_marriage",
    "vid_matt_24_2_to_matt_24_4_eschaton",
    "vid_matt_25_12_to_matt_25_26_parables",
    "vid_matt_26_23_to_matt_26_33_passion",
    "vid_luke_11_51_to_luke_17_17_prophets",
    "vid_luke_17_18_to_luke_19_40_samaritan",
    "vid_luke_20_3_to_luke_20_4_authority",
    "vid_luke_23_40_to_luke_24_18_cross_road",
    "vid_rev_9_13_to_rev_18_23_trumpet_babylon",
    "vid_gen_1_7_to_gen_1_8_creation_waters",
    "vid_gen_19_24_to_gen_20_2_sodom_abimelech",
    "vid_gen_24_1_to_gen_24_17_isaac_rebekah",
    "vid_gen_27_18_to_gen_27_41_jacob_deception",
    "vid_jhn_19_32_to_jhn_19_34_blood_water",
)


@pytest.fixture(scope="module")
def p10_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p10_chain_v1.py",
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


def test_narrative_one_forty_four(p10_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 144
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_sixty_four(p10_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 64


def test_p10_eval_inter_hop_bloom(p10_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 144
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 146
    assert len(slice_doc.get("narrative_path_samples") or []) >= 144
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_jhn_blood") == NEW_IDS[15]
