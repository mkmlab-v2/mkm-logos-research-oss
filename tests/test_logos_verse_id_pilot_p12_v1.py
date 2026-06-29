"""P12 verse-id pilot batch-6 narrative 160→176 contract."""

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


@pytest.fixture(scope="module")
def p12_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p12_chain_v1.py",
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


def test_narrative_one_seventy_six(p12_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 176
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_ninety_six(p12_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 96


def test_p12_eval_inter_hop_bloom(p12_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 176
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 178
    assert len(slice_doc.get("narrative_path_samples") or []) >= 176
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_gen_joseph") == NEW_IDS[10]
