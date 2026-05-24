#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v8.json — narrative cycle v8 (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v8.json"

CANDIDATES_V8 = [
    "noah_ark_pitch", "ark_animals_two", "flood_waters_recede", "tower_babel_confusion", "abram_call_ur",
    "lot_plain_choice", "sodom_angels_visit", "abraham_three_visitors", "sarah_cakes_baked", "hagar_ishmael_well",
    "binding_isaac_ram", "jacob_wrestle_peniel", "joseph_coat_many", "dreams_sheaf_bow", "egypt_famine_store",
    "moses_red_sea", "bitter_marah_sweet", "ten_commandments_sinai", "quail_grumbling_camp", "korah_swallowed_earth",
    "bronze_serpent_lift", "balaam_donkey_speaks", "rahab_scarlet_rope", "jericho_seven_march", "achan_hidden_silver",
    "gideon_army_three_hundred", "samson_honey_lion", "delilah_hair_shorn", "eli_ark_captured", "david_spares_saul",
    "cave_adullam_hide", "nathan_you_are_man", "temple_cloud_glory", "sheba_riddle_tests", "elijah_carmel_altar",
    "elisha_bears_youths", "naaman_seven_wash", "gehazi_greedy_leprosy", "hezekiah_fifteen_years", "josiah_law_found",
    "jeremiah_field_buy", "ezekiel_dry_bones_valley", "daniel_statue_dream", "three_friends_furnace",
    "belshazzar_feast_hand", "cyrus_decree_return", "ezra_law_reading", "nehemiah_sword_and_trowel", "job_friends_debate",
    "psalm_one_tree_streams", "proverbs_ant_highway", "ecclesiastes_under_sun", "song_garden_locked",
    "isaiah_servant_songs", "jeremiah_weeping_prophet", "lamentations_city_fall", "ezekiel_temple_vision",
    "hosea_buy_back_wife", "joel_locust_army", "amos_plumb_crooked", "obadiah_edom_pride", "jonah_whale_three",
    "micah_bethlehem_ruler", "nahum_nineveh_overthrow", "habakkuk_faith_wait", "zephaniah_silent_day",
    "haggai_consider_paths", "zechariah_branch_temple", "malachi_messenger_coming", "matthew_sermon_mount",
    "beatitudes_peacemakers", "mark_storm_stilled", "luke_samaritan_inn", "john_vine_branches", "acts_pentecost_wind",
    "galatians_fruit_spirit_list", "ephesians_armor_belt", "philippians_press_goal", "colossians_supremacy_christ",
    "thessalonians_thief_night", "timothy_good_fight", "titus_crete_island", "philemon_onesimus_plea",
    "hebrews_faith_cloud", "james_tongue_rudder", "peter_feed_sheep", "john_love_command", "revelation_lamb_throne",
    "twenty_four_elders", "seven_trumpet_woes", "seven_bowls_wrath", "new_jerusalem_descends",
    "tree_life_healing_leaves", "alpha_omega_amen", "faithful_witness_come", "census_bethlehem_travel",
    "manger_shepherds_angels", "magi_gold_frankincense", "flight_egypt_herod", "return_nazareth_child",
    "jordan_baptism_dove", "transfiguration_white_robes", "last_supper_cup", "gethsemane_bloody_sweat",
    "betrayal_garden_kiss", "pilate_barabbas_vote", "crown_thorns_mock", "crucifixion_noon_dark",
    "tomb_stone_rolled", "resurrection_road_emmaus", "ascension_olive_cloud", "adam_serpent_curse",
    "eve_mother_all_living", "cain_abel_offerings", "enoch_walked_with_god", "noah_found_grace",
    "abraham_stars_count", "isaac_wells_dug",
]

META_V8 = {
    **META,
    "revelation_lamb_slain": ("어린 양 보좌", "요한계시록 5:6", "보좌와 네 생물 사이에", "중앙 메트릭·희생 배포 비유"),
    "corinth_love_never_fails": ("사랑은 끝없음", "고린도전서 13:8", "사랑은 언제까지나 떨어지지 않으니", "SLO 지속·회귀 복원력 비유"),
    "gethsemane_sweat_blood": ("겟세마네 땀", "누가복음 22:44", "땀이 땅에 떨어지기까지", "고부하 인시던트·온콜 압박 비유"),
}


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in range(1, 9):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_v{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in CANDIDATES_V8 if c not in on_disk and not c.endswith("_alt")]

    meta = META_V8
    out: list[dict] = []
    for slug in slugs:
        if slug in meta:
            ko, ref, txt, core = meta[slug]
            theme = f"{ko} ({title(slug)})"
            note = f"{core}이며 [HYPO] Track A·실매매 단정 아님."
        else:
            theme = f"{title(slug)} (Track B)"
            ref, txt = "시편 119:105", "주의 말씀은 내 발에 등이요"
            note = f"{title(slug)} 은유는 B-track ops·거버넌스 비유이며 [HYPO] 단정 아님."
        out.append(
            {"slug": slug, "theme": theme, "anchor_ref": ref, "anchor_text": txt, "note": note}
        )

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} -> {OUT}")
    if out:
        print(f"range {out[0]['slug']} .. {out[-1]['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
