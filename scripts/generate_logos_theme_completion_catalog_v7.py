#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v7.json — ceremony/church-cycle slugs (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v7.json"

POOL_V7 = """
adam_earth dust adam_naming animals ark_raven olive_branch babel_languages
abraham_tent melchizedek_bread covenant_rainbow sarah_laugh hagar_angel
lot_veil sodom_brimstone isaac_well rebekah_camels jacob_ladder_dream
joseph_dream_coat benjamin_bowl judah_tamar moses_basket reeds
plague_darkness passover_door blood lintel pillar_fire_night manna_quail
calf_worship tablets_broken covenant_renewed spies_cluster joshua_horn
jericho_shout achan_stolen sun_moon_stood gideon_pitchers jephthah_daughter
samson_gates delilah_scissors eli_lamp samuel_voice saul_tall
david_anointed harp_soothe goliath_armor bathsheba_uriah nathan_parable
solomon_temple ark_glory queen_sheba gifts elijah_raven_feed
widow_oil jar elisha_shunem_room naaman_river dip gehazi_leprosy
hezekiah_sundial isaiah_coal tongue josiah_huldah jeremiah_cistern_mud
ezekiel_bones breath daniel_three_friends furnace belshazzar_mene
cyrus_decree ezra_reading nehemiah_gates job_satan_allowed friends_ashes
psalm_23_rod proverbs_31_woman ecclesiastes_seasons song_vineyard
isaiah_6_coal jeremiah_18_potter ezekiel_37_army hosea_gomer
joel_spirit_pour amos_5_justice obadiah_edom pride jonah_fish
micah_4_mountain nahum_nineveh_fall habakkuk_2_write zephaniah_day_wrath
haggai_consider zechariah_4_lampstand malachi_3_rob titus_crete
matthew_tax_collector mark_leper_touch luke_samaritan priest levite
john_woman_well acts_lydda_tabitha corinth_love_chapter galatians_crucified
ephesians_one_body philippians_christ_mind colossians_hidden_treasure
thessalonians_day_lord timothy_stir_gift titus_sound_doctrine philemon_onesimus
hebrews_11_cloud james_visit_orphans peter_denial_rooster john_beloved_disciple
jude_contend faith revelation_4_throne lamb_book seven_seals trumpet_woe
bowl_pour harlot_babylon beast_rising false_prophet millennium_bind
new_earth_no_tears alpha_omega_begin end river_life tree_fruit_month
golden_candlestick seven_stars lampstand_two witnesses olive lampstands
white_robes palm_branches sea_glass crystal_city gates_pearl
census_david plague_option uriah_letter absalom_gate joab_census
ahab_vineyard naboth_vineyard jezebel_dogs jehu_chariot_race
jehoiada_crown boy_king joash_repair_temple manasseh_idols
zephaniah_hidden_day haggai_zerubbabel_temple zechariah_horses_patrol
matthew_fishers men mark_withered_hand sabbath_grain
luke_prodigal_father ring_robe fatted_calf elder_brother
john_lazarus_sister mary_anointing costly_nard
acts_ananias_vision cornelius_sheet peter_rooftop
romans_abraham_faith galatians_freedom_law ephesians_husband_wife
philippians_press_prize colossians_put_off_self
hebrews_better_covenant revelation_ephesus_lampstand
smyrna_poverty pergamos_nicolaitans thyatira_jezebel sardis_wake
philadelphia_door laodicea_lukewarm buy_gold_salve knock_door
""".split()

META_V7 = {
    **META,
    "revelation_4_throne": ("보좌 둘러섬", "요한계시록 4:2", "보좌에 앉으신 이가 계시매", "관측 대시보드·중앙 제어 비유"),
    "seven_seals": ("일곱 인", "요한계시록 5:1", "일곱 인으로 봉한 책", "단계적 공개·릴리스 게이트 비유"),
    "laodicea_lukewarm": ("라오디게아 미지근", "요한계시록 3:16", "네가 미지근하여", "SLO 미달·알람 임계 비유"),
    "psalm_23_rod": ("시편 23 장막", "시편 23:4", "주의 지팡이와 막대기가", "런북·온콜 에스컬레이션 비유"),
}


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in ("v1", "v2", "v3", "v4", "v5", "v6", "v7"):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    seen: set[str] = set()
    slugs: list[str] = []
    for c in POOL_V7:
        if c in on_disk or c in seen or c.endswith("_alt"):
            continue
        seen.add(c)
        slugs.append(c)
        if len(slugs) >= 118:
            break

    meta = META_V7
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
