#!/usr/bin/env python3
"""Export compact cosmic-anchor graph bridge slice for mkmlife OrbGraphBloom ([HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bloom_slice_v1_latest.json"
OUT_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"
)

PRESET_NARRATIVE_MAP = {
    "job_suffering_reason": "isa53_wound_to_jhn_light",
    "motif_light": "isa53_wound_to_jhn_light",
    "motif_door": "vine_to_door_abiding_access",
    "motif_star": "seed_to_way_core",
    "motif_restoration": "wrath_to_healing_restoration",
    "motif_abiding": "vine_to_door_abiding_access",
    "motif_shepherd": "shepherd_to_door_pastoral",
    "motif_covenant": "blood_to_cross_covenant",
    "motif_fire": "fire_to_rock_refuge",
    "motif_ark": "ark_to_star_eschaton",
    "motif_winnow": "chaff_to_fire_winnow",
    "motif_liberation": "bondage_to_harbor_liberation",
    "motif_abundance": "oil_to_honey_abundance",
    "motif_preservative": "salt_to_light_preservative",
    "motif_lament": "ashes_to_healing_restoration",
    "motif_peace": "dove_to_olive_covenant",
    "motif_provision": "fish_to_bread_provision",
    "motif_epiphany": "darkness_to_light_epiphany",
    "motif_soar": "eagle_to_rock_soar",
    "motif_wilderness": "famine_to_manna_wilderness",
    "motif_harvest": "wheat_to_bread_harvest",
    "motif_refuge": "cloak_to_shelter_refuge",
    "motif_covenant_cup": "cup_to_wine_covenant",
    "motif_freedom": "chains_to_deliverance_freedom",
    "motif_sweetness": "bitterness_to_honey_sweetness",
    "motif_blindness": "blindness_to_healing_sight",
    "motif_exile": "exile_to_harbor_return",
    "motif_fortress": "fortress_to_rock_bastion",
    "motif_flood": "flood_judgment_to_ark_salvation",
    "motif_earthquake": "earthquake_to_rock_tremor",
    "motif_parable": "fig_to_vine_parable",
    "motif_petition": "daily_bread_to_bread_petition",
    "motif_covering": "garment_to_cloak_covering",
    "motif_refinement": "furnace_to_fire_refinement",
    "motif_stormbreak": "dark_cloud_to_light_stormbreak",
    "motif_judgment": "curse_to_ashes_judgment",
    "motif_armor": "breastplate_to_shield_armor",
    "motif_hearing": "deaf_to_healing_hearing",
    "motif_kingdom": "mustard_to_seed_kingdom",
    "motif_ferment": "leaven_to_bread_ferment",
    "motif_nourishment": "milk_to_honey_nourishment",
    "motif_lion": "lion_to_shepherd_kingdom",
    "motif_guidance": "lamp_to_light_guidance",
    "motif_cleansing": "leprosy_to_healing_cleansing",
    "motif_home": "nest_to_shelter_home",
    "motif_warfare": "helmet_to_shield_warfare",
    "motif_plague": "locust_to_famine_plague",
    "motif_trial": "persecution_to_deliverance_trial",
    "motif_harvest_net": "net_to_fish_harvest",
    "motif_treasure": "gold_to_honey_treasure",
    "motif_hail": "hail_to_fire_judgment",
    "motif_shadow": "shadow_to_light_emergence",
    "motif_rest": "rest_to_still_waters_peace",
    "motif_storm": "storm_to_rock_shelter",
    "motif_revival": "spring_to_living_water_revival",
    "motif_victory": "serpent_to_cross_victory",
    "motif_bastion": "stronghold_to_fortress_bastion",
    "motif_endurance": "tribulation_to_deliverance_endurance",
    "motif_comfort": "weeping_to_healing_comfort",
    "motif_wing": "wing_to_eagle_shelter",
    "motif_humility": "worm_to_ashes_humility",
    "motif_sword": "sword_to_shield_warfare",
    "motif_watchtower": "tower_to_fortress_watch",
    "motif_haven": "refuge_to_shelter_haven",
    "motif_burden": "millstone_to_rock_burden",
    "motif_death_cross": "death_to_cross_victory_redeemed",
    "motif_anchor_hope": "anchor_rope_to_harbor_hope",
    "motif_staff_guidance": "rod_staff_to_staff_guidance",
    "motif_desolation": "desolation_to_ashes_lament",
    "motif_unquenchable": "fire_unquenchable_to_fire_judgment",
    "motif_gathering": "fold_to_shepherd_gathering",
    "motif_foundation": "stumbling_to_rock_foundation",
    "motif_fellowship": "table_to_bread_fellowship",
    "motif_suffering": "thorn_to_wound_suffering",
    "motif_wealth": "treasure_to_gold_wealth",
    "motif_pasture_rest": "green_pasture_to_pasture_rest",
    "motif_affliction": "pestilence_to_plague_affliction",
    "vid_creation": "vid_gen_1_1_to_gen_1_3_creation_light",
    "vid_flood": "vid_gen_6_3_to_gen_7_1_flood_judgment",
    "vid_covenant": "vid_gen_15_5_to_gen_17_1_promise_covenant",
    "vid_pilot_anchor": "vid_gen_28_17_to_gen_28_5_bethel_encounter",
    "vid_matt_baptism": "vid_matt_3_10_to_matt_3_15_baptism",
    "vid_luke_annunciation": "vid_luke_1_19_to_luke_1_35_annunciation",
    "vid_rev_witnesses": "vid_rev_11_1_to_rev_11_6_two_witnesses",
    "vid_gen_abram": "vid_gen_13_14_to_gen_14_19_abram_call",
    "vid_matt_parables": "vid_matt_12_47_to_matt_13_11_parables",
    "vid_luke_sabbath": "vid_luke_13_2_to_luke_13_14_sabbath",
    "vid_rev_babylon": "vid_rev_18_8_to_rev_19_16_babylon",
    "vid_gen_creation_day": "vid_gen_1_5_to_gen_1_10_creation_day",
    "vid_matt_passion": "vid_matt_26_23_to_matt_26_33_passion",
    "vid_luke_emmaus": "vid_luke_23_40_to_luke_24_18_cross_road",
    "vid_jhn_blood": "vid_jhn_19_32_to_jhn_19_34_blood_water",
    "vid_gen_isaac": "vid_gen_24_1_to_gen_24_17_isaac_rebekah",
    "vid_matt_resurrection": "vid_matt_28_5_to_matt_3_11_resurrection",
    "vid_heb_tabernacle": "vid_heb_9_3_to_heb_9_14_tabernacle",
    "vid_acts_mission": "vid_acts_5_29_to_acts_8_34_mission",
    "vid_gen_creation_man": "vid_gen_1_25_to_gen_2_6_creation_man",
    "vid_gen_flood_arc": "vid_gen_6_7_to_gen_8_2_flood",
    "vid_gen_joseph": "vid_gen_29_14_to_gen_37_14_joseph",
    "vid_lev_clean": "vid_lev_11_16_to_lev_11_29_clean",
    "vid_jer_judgment": "vid_jer_8_2_to_jer_16_4_judgment",
    "vid_gen_dove": "vid_gen_8_8_to_gen_8_16_dove",
    "vid_cross_nt_ot": "vid_jhn_19_33_to_heb_9_5_passion",
    "vid_temple_covenant": "vid_2chr_6_25_to_hos_2_20_temple_covenant",
    "vid_gen_closure": "vid_gen_42_21_to_gen_49_16_joseph_blessing",
    "vid_gen_covenant_sign": "vid_gen_8_19_to_gen_8_9_covenant_sign",
}


def build_slice(bridge: dict[str, Any], *, resonance_cap: int = 128) -> dict[str, Any]:
    edges = list(bridge.get("resonance_edges") or [])
    edges.sort(key=lambda row: float(row.get("weight") or 0), reverse=True)
    return {
        "schema": "logos_cosmic_anchor_graph_bloom_slice_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "resonance_cap": resonance_cap,
        "kernel_recipe_id": bridge.get("kernel_recipe_id", "gematria_bridge_v1"),
        "anchor_count": int(bridge.get("anchor_count") or 0),
        "summary": bridge.get("summary") or {},
        "preset_narrative_map": dict(PRESET_NARRATIVE_MAP),
        "narrative_path_samples": list(bridge.get("narrative_path_samples") or []),
        "resonance_edges_top": edges[:resonance_cap],
        "source_bridge_schema": bridge.get("schema"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out-artifact", type=Path, default=OUT_ART)
    parser.add_argument("--out-public", type=Path, default=OUT_PUBLIC)
    parser.add_argument("--resonance-cap", type=int, default=128)
    args = parser.parse_args()

    if not args.bridge_json.is_file():
        print(f"FAIL: missing bridge {args.bridge_json}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    doc = build_slice(bridge, resonance_cap=args.resonance_cap)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_public.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(payload, encoding="utf-8")
    args.out_public.write_text(payload, encoding="utf-8")
    print(
        f"WROTE: {args.out_artifact}\n"
        f"  narratives={len(doc['narrative_path_samples'])} "
        f"resonance_top={len(doc['resonance_edges_top'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
