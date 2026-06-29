"""P7 verse-id pilot narrative 80→96 contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
EVAL = ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json"
SLICE = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
INTER = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"

PILOT_IDS = (
    "vid_gen_1_1_to_gen_1_3_creation_light",
    "vid_gen_1_2_to_gen_1_6_firmament",
    "vid_gen_1_9_to_gen_1_14_lights",
    "vid_gen_1_20_to_gen_1_24_creature_kind",
    "vid_gen_1_27_to_gen_1_28_image_blessing",
    "vid_gen_2_5_to_gen_2_7_formed_life",
    "vid_gen_3_9_to_gen_3_14_fall_judgment",
    "vid_gen_6_3_to_gen_7_1_flood_judgment",
    "vid_gen_8_1_to_gen_8_7_dry_land",
    "vid_gen_9_18_to_gen_11_4_covenant_tower",
    "vid_gen_15_5_to_gen_17_1_promise_covenant",
    "vid_gen_22_15_to_gen_25_23_sacrifice_line",
    "vid_gen_28_17_to_gen_28_5_bethel_encounter",
    "vid_exod_21_20_to_exod_24_4_law_covenant",
    "vid_acts_16_26_to_acts_25_9_mission_trial",
    "vid_deut_14_15_to_deut_26_15_statute_pledge",
)


@pytest.fixture(scope="module")
def p7_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_verse_id_pilot_p7_chain_v1.py",
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


def test_narrative_ninety_six_with_pilot_paths(p7_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 96
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in PILOT_IDS:
        assert sid in samples


def test_pilot_paths_tagged_verse_id(p7_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    pilot = [s for s in bridge.get("narrative_path_samples") or [] if s["sample_id"] in PILOT_IDS]
    assert len(pilot) == 16
    for row in pilot:
        assert "VERSE-ID-PILOT" in str(row.get("query_ko") or "")


def test_p7_eval_and_inter_hop(p7_chain: None) -> None:
    eval_doc = json.loads(EVAL.read_text(encoding="utf-8"))
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert eval_doc["narrative_sample_count"] >= 96
    assert eval_doc["summary"]["sample_pass_rate"] == 1.0
    assert inter["summary"]["inter_hop_pair_count"] >= 98
    assert len(slice_doc.get("narrative_path_samples") or []) >= 96
    assert slice_doc.get("preset_narrative_map", {}).get("vid_creation") == PILOT_IDS[0]


def test_pilot_uses_verse_id_stems(p7_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    stem_by_id = {r["anchor_id"]: r["file_stem"] for r in bridge["per_anchor"]}
    pat = re.compile(r"^[a-z0-9]+_\d+_\d+$")

    def is_verse_id(st: str) -> bool:
        return bool(pat.match(st))

    for sample in bridge.get("narrative_path_samples") or []:
        if not str(sample.get("sample_id") or "").startswith("vid_"):
            continue
        for hop in sample.get("path") or []:
            stem = stem_by_id.get(str(hop.get("anchor_id") or ""), "")
            assert is_verse_id(stem), f"expected verse-id stem, got {stem}"
