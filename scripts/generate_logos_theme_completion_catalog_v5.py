#!/usr/bin/env python3
"""Generate logos_theme_completion_catalog_v5.json — v5b extended slugs (Track B)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generate_logos_theme_completion_catalog_v3 import META, title

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "docs/research/logos_metaphor_db_v1"
OUT = ROOT / "scripts/data/logos_theme_completion_catalog_v5.json"
CANDIDATES_PATH = ROOT / "scripts/data/logos_theme_completion_candidates_v5_v1.json"

CANDIDATES_V5B = [
    "creation_sabbath", "sabbath_creator", "abraham_oath", "isaac_wells_dig", "jacob_peeled_rods",
    "leah_weak_eyes", "rachel_beautiful", "benjamin_wolf", "dan_serpent", "naphtali_deer",
    "issachar_donkey", "zebulun_haven", "asher_bread", "gad_troop", "manasseh_vine",
    "ephraim_fruit", "simeon_sword", "reuben_water", "judah_lion_cub", "moses_mechuzoth",
    "aaron_budding_rod", "korah_incense", "aaron_rod_bud", "serpent_fiery", "balak_balaam",
    "moab_seduction", "phinehas_zeal", "joshua_caleb", "othniel_captor", "gideon_fleece_dew",
    "samson_riddle", "samson_delilah", "ruth_boaz_field", "eli_ark_taken", "samuel_anoints_saul",
    "david_nabal", "abigail_peacemaker", "absalom_oak_hair", "solomon_proverbs", "queen_sheba_riddles",
    "elijah_mount_carmel", "ahab_naboth", "jehu_furious", "joash_crown", "hezekiah_sundial_back",
    "manasseh_altar", "josiah_book_found", "jeremiah_linen_belt", "ezekiel_wheels", "daniel_stone",
    "belshazzar_hand", "cyrus_issued", "ezra_scribe", "nehemiah_governor", "esther_courage",
    "job_ash_heap", "psalm_shepherd", "proverbs_woman", "ecclesiastes_vanity", "song_beloved",
    "isaiah_virgin", "jeremiah_potter_clay", "lamentations_city", "ezechiel_dry", "daniel_lions_den",
    "hosea_unfaithful", "joel_locusts", "amos_plumbline", "obadiah_proud", "jonah_gourd_shade",
    "micah_swords_beat", "nahum_runner", "habakkuk_watchtower", "zephaniah_day_silent",
    "haggai_temple_rebuild", "zechariah_branch", "malachi_sun_healing", "matthew_genealogy",
    "mark_urgency", "luke_compassion", "john_light", "acts_spread", "romans_gospel",
    "corinthians_body", "galatians_freedom", "ephesians_armor", "philippians_joy", "colossians_head",
    "thessalonians_wait", "timothy_young", "titus_island_pastor", "philemon_slave", "hebrews_rest_promised",
    "james_tongue_fire", "peter_rock", "john_love", "jude_contend_faith", "revelation_lamb_slain",
    "genesis_beginning", "exodus_deliverance", "leviticus_holiness", "numbers_wilderness",
    "deuteronomy_law_repeat", "joshua_promised_land", "judges_cycle", "ruth_loyalty", "samuel_transition",
    "kings_divided", "chronicles_retell", "ezra_restoration", "nehemiah_wall_build", "esther_providence",
    "job_suffering_wisdom", "psalms_worship", "proverbs_wisdom_daily", "ecclesiastes_meaning",
    "song_union", "major_prophets", "minor_prophets_twelve", "gospel_fourfold", "epistles_pauline",
    "pastoral_epistles", "general_epistles", "apocalypse_unveiling",
]

META_V5 = {
    **META,
    "daniel_lions_den": ("다니엘 사자굴", "다니엘 6:22", "하나님이 그 천사를 보내어", "격리 환경 생존·복원력 비유"),
    "ezekiel_wheels": ("에스겔 바퀴", "에스겔 1:16", "바퀴의 모양과 행위는", "분산 오케스트레이션·순환 의존성 비유"),
    "ephesians_armor": ("에베소 갑옷", "에베소서 6:11", "하나님의 전신갑주를", "보안 레이어 스택 비유"),
    "revelation_lamb_slain": ("어린 양", "요한계시록 5:6", "보좌 가운데에", "감사·희생 메트릭 비유"),
    "apocalypse_unveiling": ("요한 계시", "요한계시록 1:1", "일은 가까우니", "관측성 공개·런북 unveil 비유"),
}


def _on_disk_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    for v in ("v1", "v2", "v3", "v4", "v5"):
        p = ROOT / f"scripts/data/logos_theme_completion_catalog_{v}.json"
        if p.is_file():
            for c in json.loads(p.read_text(encoding="utf-8")):
                slugs.add(c["slug"])
    if CANDIDATES_PATH.is_file():
        for slug in json.loads(CANDIDATES_PATH.read_text(encoding="utf-8")):
            slugs.add(str(slug))
    return slugs


def main() -> int:
    on_disk = _on_disk_slugs()
    slugs = [c for c in CANDIDATES_V5B if c not in on_disk and not c.endswith("_alt")]
    out: list[dict] = []
    meta = META_V5
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
