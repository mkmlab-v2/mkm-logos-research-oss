#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v6.json — narrative/parable slugs (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v6.json"

CANDIDATES_V6 = [
    "abel_firstling", "adam_rib", "ark_dove", "balaam_star", "barnabas_land",
    "beersheba_oath", "bethlehem_star", "bread_wine_last", "burning_bush_unburnt", "cain_abel_offer",
    "cana_wedding", "cloud_pillar_night", "cornelius_peter", "creation_light_day", "curse_babel",
    "daniel_prayer_open", "david_bethlehem", "david_cave_adullam", "denarius_workers", "drought_elijah",
    "eden_guardian", "elisha_shunammite", "elijah_ravens_brook", "enoch_translation", "esau_hairy",
    "eve_seed", "exodus_manna", "faithful_servant", "fig_tree_cursed", "fire_sodom",
    "five_loaves", "flood_rainbow_sign", "gad_seer", "gentile_centurion", "gideon_trumpets",
    "golden_rule", "good_seed_weeds", "healing_pool_bethesda", "heavenly_host", "herod_fox",
    "holy_ground_shoes", "holy_of_holies", "holy_spirit_dove", "isaac_blessing_jacob", "isaac_marriage",
    "jairus_daughter_raise", "jericho_march", "jesus_temptation", "jochebed_basket", "john_baptist_behead",
    "jonah_three_days", "joseph_prison_dream", "joshua_commander", "judas_silver", "lazarus_four_days",
    "light_under_bushel", "logos_word", "lot_salt", "loaves_blessing", "manna_corruption",
    "martha_mary", "melchizedek_king", "mercy_good_samaritan", "micaiah_true", "miracle_cana",
    "mustard_seed_kingdom", "naomi_bitterness", "new_wine_skins", "noah_ark_window", "olive_mount_ascend",
    "paul_shipwreck", "pharaoh_dream_cows", "pilate_barabbas", "pool_siloam", "prophet_without_honor",
    "rebecca_well", "road_damascus", "rock_christ", "rod_staff_comfort", "roman_centurion",
    "sabbath_manborn", "samaria_woman", "samaritan_lepers", "saul_damascus", "seven_deacons",
    "siloam_tower", "sinai_thunder", "sower_four_soils", "spirit_helper", "storm_stilled",
    "temple_tax_coin", "thief_cross", "three_temptations", "transfiguration_glory", "tree_known_fruit",
    "triumphal_palm", "twelve_stones", "upper_room_prayer", "water_rock_strike", "winepress_wrath",
    "whitened_harvest", "woman_issue_blood", "zealots_sword", "zaccheus_restitution",
    "abraham_intercedes", "lot_angels", "hagar_well", "ishmael_bow", "isaac_altar",
    "jacob_stone_pillow", "leah_mandrakes", "joseph_storehouse", "moses_brass_snake", "aaron_golden_calf",
    "spies_grapes", "rahab_house", "gideon_army", "samson_jawbone",
]

META_V6 = {
    **META,
    "burning_bush_unburnt": ("불타지 않는 떨기나무", "출애굽기 3:2", "떨기나무가 불붙었으나 타지 아니하니", "이상 징후·프리플라이트 점검 비유"),
    "logos_word": ("말씀 로고스", "요한복음 1:1", "태초에 말씀이 계시니라", "SSOT 스키마·단일 진실 비유"),
    "sower_four_soils": ("씨 뿌리는 자", "마태복음 13:8", "백 배, 육십 배, 삼십 배", "트래픽 품질·채널별 전환 비유"),
    "road_damascus": ("다메섹 도상", "사도행전 9:3", "홀연히 하늘로부터 빛이", "인시던트 전환·아키텍처 피벗 비유"),
    "lazarus_four_days": ("나사로 사흘", "요한복음 11:39", "죽은 지 나흘이 되었나이다", "장기 장애·딥 리커버리 비유"),
    "transfiguration_glory": ("변화산 영광", "마태복음 17:2", "얼굴이 해 같이 빛나며", "스테이징 프리뷰·일시 고가용 비유"),
}


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in ("v1", "v2", "v3", "v4", "v5", "v6"):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in CANDIDATES_V6 if c not in on_disk and not c.endswith("_alt")]
    meta = META_V6
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
