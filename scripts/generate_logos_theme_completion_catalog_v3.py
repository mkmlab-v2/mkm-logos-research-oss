#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v3.json (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v3.json"

CANDIDATES = [
    "alpha_omega_throne", "amos_basket", "babylon_fallen", "beast_sea", "dragon_cast",
    "joshua_sun_stand", "lost_coin_parable", "lost_sheep_parable", "marriage_supper",
    "new_jerusalem_gate", "seal_forehead", "throne_white", "two_witnesses", "woman_clothed",
    "ark_noah_raven", "babel_gate", "birth_esau", "birth_jacob", "blessing_jacob", "blessing_joseph",
    "blood_passover", "bondservant_paul", "book_life", "bow_rainbow", "branch_jesse", "bread_melchizedek",
    "burning_sulfur", "calf_gold", "call_abraham", "call_moses", "call_samuel", "census_moses", "chains_paul",
    "chariot_fire", "child_laugh", "chosen_david", "cloud_glory", "coal_altar", "covenant_abraham",
    "covenant_david", "covenant_noah", "creation_man", "curse_ground", "day_atonement", "death_absalom",
    "denial_peter", "desert_elijah", "dove_spirit", "dream_joseph", "dry_bones", "eagle_wings", "eden_expelled",
    "elisha_double", "endurance_job", "esau_soup", "eve_fruit", "exile_return", "faith_abraham", "fall_tower",
    "famine_world", "fast_esther", "fear_not", "field_harvest", "fire_pentecost", "firstborn_death", "flood_noah",
    "forgive_seventy", "fountain_life", "four_winds", "garment_salvation", "gentiles_grafted", "giant_goliath",
    "glory_tabernacle", "god_provides", "golden_incense", "good_cheer", "gospel_preach", "grace_sufficient",
    "grapes_wild", "handwriting_wall", "healing_nations", "heart_circumcise", "heaven_opened", "hell_gehenna",
    "holy_spirit", "hope_anchor", "horn_salvation", "hosanna_cry", "image_daniel", "incense_prayer",
    "inheritance_lot", "israel_stiff", "jordan_cross", "joy_salvation", "judgment_seat", "kingdom_parables",
    "lamb_passover", "lamp_oil", "law_grace", "leaven_sins", "light_world", "lion_judah", "living_stone",
    "loaves_fishes", "love_enemies", "man_sower", "manna_heaven", "mark_cain", "marriage_king", "mercy_seat",
    "messiah_anointed", "millstone_neck", "miracle_sign", "miry_clay", "mount_olives", "mountain_zion",
    "mustard_faith", "name_jesus", "new_wine", "night_watch", "oil_anoint", "olive_tree", "open_grave",
    "oracle_balaam", "overcomer_crown", "patience_job", "peace_prince", "pentecost_flame", "persecution_blessed",
    "pharaoh_dreams", "pillar_fire", "plague_locusts", "potter_clay", "power_spirit", "praise_temple",
    "prayer_fervent", "priest_melchizedek", "promise_land", "prophecy_fulfill", "providence_god", "pure_heart",
    "rain_latter", "redeemer_boaz", "refiner_fire", "repent_baptize", "rest_sabbath", "resurrection_body",
    "righteous_lot", "river_eden", "rock_moses", "rod_iron", "root_jesse", "sabbath_rest", "sacrifice_praise",
    "salt_covenant", "sanctuary_god", "scroll_ezekiel", "second_death", "seed_word", "servant_moses",
    "seven_spirits", "shepherd_king", "sign_covenant", "sin_scapegoat", "sower_word", "spirit_truth",
    "star_bethlehem", "stone_rolled", "storm_calmed", "strong_delusion", "suffering_christ", "tabernacle_god",
    "temple_body", "tent_meeting", "test_abraham", "thorn_crown", "three_hebrews", "threshing_floor",
    "tithe_melchizedek", "tongue_control", "tower_siloam", "tree_planted", "tribulation_saints", "trumpet_judgment",
    "truth_sets_free", "unity_spirit", "valley_decision", "vine_true", "voice_lamb", "walk_emmaus", "wall_jericho",
    "war_heaven", "watchman_wall", "water_baptism", "way_truth_life", "wheat_harvest", "whirlwind_god", "widow_oil",
    "wilderness_test", "wine_blood", "wisdom_solomon", "witness_cloud", "woman_wisdom", "word_incarnate", "wrath_lamb",
    "yoke_easy", "zeal_house", "zion_hill",
]

META = {
    "dry_bones": ("마른 뼈", "에스겔 37:7", "뼈들이 서로 연결되며", "드라이런 복구·스켈레톤 서비스 비유"),
    "potter_clay": ("토기장이 진흙", "예레미야 18:6", "진흙과 같이 나를 다루실", "설정 재구성·리셰이프 비유"),
    "wall_jericho": ("여리고 성벽", "여호수아 6:20", "성이 무너지매", "방화벽 제거·카나리 통과 비유"),
    "way_truth_life": ("길 진리 생명", "요한복음 14:6", "내가 길이요 진리요", "SSOT 라우팅·단일 진입점 비유"),
    "book_life": ("생명책", "요한계시록 20:12", "죽은 자들이 그 책들을", "감사 로그·불변 ledger 비유"),
    "babylon_fallen": ("바벨론 패망", "요한계시록 18:2", "큰 바벨론이 무너졌도다", "레거시 모놀리스 종료 비유"),
    "lukewarm_laodicea": ("라오디게아", "요한계시록 3:16", "네가 미지근하여", "SLO 미달 경고 비유"),
}


def title(slug: str) -> str:
    return slug.replace("_", " ").title()


def main() -> int:
    on_disk: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            on_disk.add(m.group(1))
    for v in ("v1", "v2"):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                on_disk.add(c["slug"])

    slugs = [c for c in CANDIDATES if c not in on_disk and not c.endswith("_alt")][:118]
    out: list[dict] = []
    for slug in slugs:
        if slug in META:
            ko, ref, txt, core = META[slug]
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
