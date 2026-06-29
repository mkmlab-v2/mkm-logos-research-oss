"""P11 verse-id pilot batch-5 narrative 144→160 contract."""

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
    "vid_matt_20_13_to_matt_21_29_vineyard",
    "vid_matt_22_2_to_matt_23_30_wedding",
    "vid_matt_23_34_to_matt_25_27_woe",
    "vid_matt_26_25_to_matt_27_21_judas",
    "vid_matt_28_5_to_matt_3_11_resurrection",
    "vid_matt_5_23_to_matt_5_24_reconciliation",
    "vid_luke_3_11_to_luke_5_5_calling",
    "vid_luke_5_22_to_luke_5_31_healing",
    "vid_luke_6_3_to_luke_6_4_sabbath",
    "vid_luke_7_22_to_luke_8_21_messiah_family",
    "vid_gen_20_8_to_gen_21_1_isaac_birth",
    "vid_gen_21_14_to_gen_21_26_ishmael",
    "vid_gen_23_3_to_gen_24_23_sarah_rebekah",
    "vid_gen_1_25_to_gen_2_6_creation_man",
    "vid_heb_9_3_to_heb_9_14_tabernacle",
    "vid_acts_5_29_to_acts_8_34_mission",
)


@pytest.fixture(scope="module")
def p11_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p11_chain_v1.py",
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


def test_narrative_one_sixty(p11_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 160
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_verse_id_pilot_total_eighty(p11_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    vid = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"].startswith("vid_")]
    assert len(vid) >= 80


def test_p11_eval_inter_hop_bloom(p11_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 160
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 162
    assert len(slice_doc.get("narrative_path_samples") or []) >= 160
    assert slice_doc.get("resonance_cap") == 40
    assert slice_doc.get("preset_narrative_map", {}).get("vid_acts_mission") == NEW_IDS[15]
