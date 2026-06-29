"""P4 named-motif exhaust narrative 64→80 (round-2 close) contract."""

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
OVERLAP = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"

NEW_IDS = (
    "sword_to_shield_warfare",
    "tower_to_fortress_watch",
    "refuge_to_shelter_haven",
    "millstone_to_rock_burden",
    "death_to_cross_victory_redeemed",
    "anchor_rope_to_harbor_hope",
    "rod_staff_to_staff_guidance",
    "desolation_to_ashes_lament",
    "fire_unquenchable_to_fire_judgment",
    "fold_to_shepherd_gathering",
    "stumbling_to_rock_foundation",
    "table_to_bread_fellowship",
    "thorn_to_wound_suffering",
    "treasure_to_gold_wealth",
    "green_pasture_to_pasture_rest",
    "pestilence_to_plague_affliction",
)

UNUSED_NAMED_STEMS = (
    "anchor_rope",
    "death",
    "desolation",
    "fire_unquenchable",
    "fold",
    "green_pasture",
    "millstone",
    "pasture",
    "pestilence",
    "refuge",
    "rod_staff",
    "staff",
    "stumbling",
    "sword",
    "table",
    "thorn",
    "tower",
    "treasure",
)


@pytest.fixture(scope="module")
def motif_exhaust_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_narrative_path_p4_motif_exhaust_chain_v1.py",
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


def test_narrative_eighty_and_new_paths(motif_exhaust_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert bridge["summary"]["narrative_sample_count"] >= 80
    samples = {s["sample_id"] for s in bridge.get("narrative_path_samples") or []}
    for sid in NEW_IDS:
        assert sid in samples


def test_named_motif_stems_exhausted(motif_exhaust_chain: None) -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    stem_by_id = {r["anchor_id"]: r["file_stem"] for r in bridge["per_anchor"]}
    used: set[str] = set()
    for sample in bridge.get("narrative_path_samples") or []:
        for hop in sample.get("path") or []:
            stem = stem_by_id.get(str(hop.get("anchor_id") or ""))
            if stem:
                used.add(stem)

    def is_named(st: str) -> bool:
        return not re.match(r"^[a-z0-9]+_\d+_\d+$", st) and not re.match(r"^[a-z]+_\d+_\d+$", st)

    all_named = {r["file_stem"] for r in bridge["per_anchor"] if is_named(r["file_stem"])}
    unused = sorted(all_named - used)
    assert unused == [], f"named motifs still unused: {unused}"


def test_motif_exhaust_eval_contract(motif_exhaust_chain: None) -> None:
    doc = json.loads(EVAL.read_text(encoding="utf-8"))
    assert doc["narrative_sample_count"] >= 80
    assert doc["summary"]["path_ok_rate"] == 1.0
    assert doc["summary"]["sample_pass_rate"] == 1.0


def test_motif_exhaust_inter_hop_and_bloom(motif_exhaust_chain: None) -> None:
    inter = json.loads(INTER.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    slice_doc = json.loads(SLICE.read_text(encoding="utf-8"))
    assert inter["summary"]["inter_hop_pair_count"] >= 82
    assert overlap["summary"]["hop_lemma_edge_hit_rate"] == 1.0
    assert overlap["summary"]["curated_bridge_pair_rate"] == 1.0
    assert len(slice_doc.get("narrative_path_samples") or []) >= 80
    pmap = slice_doc.get("preset_narrative_map") or {}
    assert pmap["motif_affliction"] == "pestilence_to_plague_affliction"
