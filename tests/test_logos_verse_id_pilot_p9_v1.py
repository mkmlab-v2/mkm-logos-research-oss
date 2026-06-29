"""P9 verse-id pilot batch-3 narrative 112→128 contract."""

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
    "vid_matt_12_47_to_matt_13_11_parables",
    "vid_matt_15_3_to_matt_15_28_syrophoenician",
    "vid_matt_15_13_to_matt_15_24_mission",
    "vid_matt_21_24_to_matt_21_30_parable",
    "vid_matt_22_1_to_matt_22_29_resurrection",
    "vid_matt_23_29_to_matt_23_35_woe",
    "vid_luke_10_41_to_luke_11_45_mary_pharisee",
    "vid_luke_13_2_to_luke_13_14_sabbath",
    "vid_luke_13_8_to_luke_14_3_dining",
    "vid_luke_15_29_to_luke_17_14_ten_lepers",
    "vid_rev_10_2_to_rev_11_1_little_book",
    "vid_rev_8_7_to_rev_8_12_trumpet",
    "vid_rev_18_8_to_rev_19_16_babylon",
    "vid_rev_18_22_to_rev_18_24_babylon_judgment",
    "vid_gen_1_5_to_gen_1_10_creation_day",
    "vid_gen_14_22_to_gen_17_3_covenant",
)


@pytest.fixture(scope="module")
def p9_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p9_chain_v1.py",
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


def test_narrative_one_twenty_eight(p9_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 128
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_forty_eight(p9_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 48


def test_p9_eval_inter_hop_bloom(p9_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 128
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 130
    assert len(slice_doc.get("narrative_path_samples") or []) >= 128
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_rev_babylon") == NEW_IDS[12]
