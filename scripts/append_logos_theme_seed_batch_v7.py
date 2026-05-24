#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v7, Track B NON_GATING)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPEND = ROOT / "docs/research/logos_metaphor_db_v1/theme_backlog_seed_pool_v1_append.jsonl"
DB = ROOT / "docs/research/logos_metaphor_db_v1"


def row(slug, theme, ref, text, nid, note, nodes):
    return {
        "slug": slug,
        "status": "pending",
        "theme": theme,
        "anchor_ref": ref,
        "anchor_text": text,
        "anchor_node_id": nid,
        "ops_analogy_note": note,
        "semantic_nodes": nodes,
    }


def n(ref, text, edge, conn, domain):
    return {
        "ref": ref,
        "text": text,
        "edge_type": edge,
        "research_metaphor_logic_connection": conn,
        "research_metaphor_domain": domain,
    }


NEW = [
    row(
        "boaz_gate",
        "보아스 문 (Boaz Gate)",
        "룻기 4:1",
        "보아스가 성문으로 올라가서",
        "ANCHOR_RUT_4_1",
        "보아스 문 은유는 공식 구제·리뷰 게이트 비유이며, 부동산이 아님.",
        [
            n("룻기 2:8", "내 소녀들과 함께 있으라", "is_stay_gleaners_of", "stay gleaners — safe sandbox", "research_metaphor_safe_sandbox"),
            n("룻기 4:9", "보아스가 장로들과 모든 백성에게", "is_witnessed_elders_of", "witnessed elders — signed approval", "research_metaphor_signed_approval"),
            n("룻기 4:13", "보아스가 룻을 맞이하여", "is_took_ruth_of", "took Ruth — merge complete", "research_metaphor_merge_complete"),
            n("갈라디아서 4:5", "율법 아래 있는 자들을", "is_redeem_under_law_of", "redeem under law — legacy buyout", "research_metaphor_legacy_buyout"),
        ],
    ),
    row(
        "elijah_still_small",
        "엘리야 잔잔한 소리 (Elijah Still Small Voice)",
        "열왕기상 19:12",
        "잔잔한 작은 소리",
        "ANCHOR_1KI_19_12",
        "잔잔한 소리 은유는 저노이 알람·미세 신호 비유이며, 음향이 아님.",
        [
            n("열왕기상 19:11", "바람이 심히 불어", "is_wind_not_of", "wind not — ignore loud alert", "research_metaphor_ignore_loud_alert"),
            n("열왕기상 19:13", "얼굴을 겉옷으로 가리고", "is_wrapped_mantle_of", "wrapped mantle — focus mode", "research_metaphor_focus_mode"),
            n("시편 46:10", "가만히 있어 내가 하나님이 됨을", "is_be_still_of", "be still — pause deploy", "research_metaphor_pause_deploy"),
            n("요한복음 10:27", "내 양은 내 음성을 듣고", "is_hear_voice_of", "hear voice — tune threshold", "research_metaphor_tune_threshold"),
        ],
    ),
    row(
        "moses_burning_bush",
        "모세 불타는 떨기 (Moses Burning Bush)",
        "출애굽기 3:2",
        "떨기나무에 불꽃이 붙었으나",
        "ANCHOR_EXO_3_2",
        "떨기불 은유는 지속 부하·이상 없는 핫스팟 비유이며, 식물이 아님.",
        [
            n("출애굽기 3:5", "신을 벗으라", "is_remove_sandals_of", "remove sandals — prod access ritual", "research_metaphor_prod_access_ritual"),
            n("출애굽기 3:10", "이제 내가 너를 애굽으로 보내리니", "is_send_egypt_of", "send Egypt — on-call page", "research_metaphor_oncall_page"),
            n("사도행전 7:30", "시내 산 광야에서", "is_sinai_bush_of", "Sinai bush — incident origin", "research_metaphor_incident_origin"),
            n("히브리서 12:18", "불 붙는 산에 이르지 못하고", "is_mountain_fire_of", "mountain fire — scary prod", "research_metaphor_scary_prod"),
        ],
    ),
    row(
        "moses_rod_snake",
        "모세 지팡이 뱀 (Moses Rod Snake)",
        "출애굽기 4:3",
        "땅에 던지매 뱀이 되니",
        "ANCHOR_EXO_4_3",
        "지팡이 뱀 은유는 도구가 위협으로 바뀌는 권한 비유이며, 동물이 아님.",
        [
            n("출애굽기 4:4", "꼬리를 잡으라", "is_grasp_tail_of", "grasp tail — reclaim control", "research_metaphor_reclaim_control"),
            n("출애굽기 7:12", "아론의 지팡이가 그들의 지팡이를 삼키니", "is_swallowed_rods_of", "swallowed rods — patch wins", "research_metaphor_patch_wins"),
            n("민수기 21:9", "놋뱀을 만들어 기둥 위에", "is_bronze_serpent_of", "bronze serpent — hotfix banner", "research_metaphor_hotfix_banner"),
            n("고린도전서 1:27", "세상에서 미련한 것들을 택하사", "is_foolish_chosen_of", "foolish chosen — humble tool", "research_metaphor_humble_tool"),
        ],
    ),
    row(
        "red_sea_cross",
        "홍해 건넘 (Red Sea Crossing)",
        "출애굽기 14:21",
        "바닷물이 갈라지고",
        "ANCHOR_EXO_14_21",
        "홍해 은유는 대규모 마이그레이션·롤백 창 비유이며, 해양이 아님.",
        [
            n("출애굽기 14:22", "물이 벽이 되어", "is_walls_water_of", "walls water — isolated lane", "research_metaphor_isolated_lane"),
            n("출애굽기 14:30", "그 날에 여호와께서 이스라엘을", "is_saved_israel_of", "saved Israel — cutover success", "research_metaphor_cutover_success"),
            n("히브리서 11:29", "홍해를 마른 땅과 같이", "is_sea_dry_of", "sea dry — impossible path works", "research_metaphor_impossible_path_works"),
            n("시편 106:9", "홍해를 광야에서 같이 말리시고", "is_dried_sea_of", "dried sea — drain queue", "research_metaphor_drain_queue"),
        ],
    ),
    row(
        "babel_confusion",
        "바벨 언어 혼잡 (Babel Confusion)",
        "창세기 11:7",
        "우리가 거기서 그들의 언어를 혼잡하게",
        "ANCHOR_GEN_11_7",
        "바벨 혼잡 은유는 스키마 드리프트·API 버전 불일치 비유이며, 언어학이 아님.",
        [
            n("창세기 11:4", "탑 꼭대기가 하늘에 닿게", "is_tower_heaven_of", "tower heaven — over-scale", "research_metaphor_over_scale"),
            n("창세기 11:9", "그 이름을 바벨이라 하니", "is_called_babel_of", "called Babel — naming incident", "research_metaphor_naming_incident"),
            n("사도행전 2:6", "각각 자기 나라 방언으로", "is_own_language_of", "own language — polyglot clients", "research_metaphor_polyglot_clients"),
            n("고린도전서 14:33", "하나님은 혼란의 하나님이 아니시요", "is_not_author_confusion_of", "not author confusion — need contract", "research_metaphor_need_contract"),
        ],
    ),
    row(
        "noah_ark",
        "노아 방주 (Noah Ark)",
        "창세기 7:1",
        "너와 온 집안은 방주로 들어가라",
        "ANCHOR_GEN_7_1",
        "방주 은유는 재해 복구 버킷·콜드 스탠바이 비유이며, 선박이 아님.",
        [
            n("창세기 6:14", "잣나무로 너를 위하여", "is_gopher_wood_of", "gopher wood — hardened image", "research_metaphor_hardened_image"),
            n("창세기 7:16", "여호와께서 그를 위하여 문을 닫으시니라", "is_lord_shut_of", "Lord shut — freeze ingress", "research_metaphor_freeze_ingress"),
            n("베드로후서 2:5", "의의 전도자 노아가", "is_noah_preacher_of", "Noah preacher — runbook owner", "research_metaphor_runbook_owner"),
            n("히브리서 11:7", "믿음으로 노아가 경고를 받아", "is_warned_faith_of", "warned faith — acted on alert", "research_metaphor_acted_on_alert"),
        ],
    ),
    row(
        "noah_rainbow",
        "노아 무지개 (Noah Rainbow)",
        "창세기 9:13",
        "내가 구름 속에 무지개를 두었나니",
        "ANCHOR_GEN_9_13",
        "무지개 은유는 장기 SLA·회복 신호 비유이며, 기상이 아님.",
        [
            n("창세기 9:15", "무지개가 구름 사이에 있을 때에", "is_bow_cloud_of", "bow cloud — status green", "research_metaphor_status_green"),
            n("이사야 54:9", "노아의 홍수 같이 다시는", "is_noah_flood_again_of", "Noah flood again — no repeat outage", "research_metaphor_no_repeat_outage"),
            n("요한계시록 4:3", "무지개와 같이 빛나는", "is_rainbow_around_of", "rainbow around — halo metric", "research_metaphor_halo_metric"),
            n("에스겔 1:28", "무지개 같은 광채로", "is_like_rainbow_of", "like rainbow — calm after storm", "research_metaphor_calm_after_storm"),
        ],
    ),
    row(
        "abraham_stars",
        "아브라함 별 (Abraham Stars)",
        "창세기 15:5",
        "하늘을 우러러 뭇 별을 셀 수 있나",
        "ANCHOR_GEN_15_5",
        "별 은유는 확장 한도·성장 상한 비유이며, 천문이 아님.",
        [
            n("창세기 22:17", "하늘의 별과 같이", "is_stars_sand_of", "stars sand — scale promise", "research_metaphor_scale_promise"),
            n("로마서 4:18", "죽은 자 같이 된 몸에서", "is_dead_body_of", "dead body — zero baseline", "research_metaphor_zero_baseline"),
            n("히브리서 11:12", "죽은 자 같이 된 몸에서", "is_as_stars_of", "as stars — burst capacity", "research_metaphor_burst_capacity"),
            n("다니엘 12:3", "지혜 있는 자는 궁창의 빛과 같이", "is_shine_firmament_of", "shine firmament — top performers", "research_metaphor_top_performers"),
        ],
    ),
    row(
        "lot_pillar",
        "롯 아내 기둥 (Lot Pillar)",
        "창세기 19:26",
        "그 뒤를 돌아보니 소금 기둥이 되었더라",
        "ANCHOR_GEN_19_26",
        "소금 기둥 은유는 롤백 거부·동결 상태 비유이며, 지질이 아님.",
        [
            n("창세기 19:17", "뒤를 돌아보거나", "is_do_not_look_of", "do not look — no rollback peek", "research_metaphor_no_rollback_peek"),
            n("누가복음 17:32", "롯의 아내를 기억하라", "is_remember_lot_wife_of", "remember Lot wife — nostalgia trap", "research_metaphor_nostalgia_trap"),
            n("마태복음 10:39", "자기 목숨을 잃는 자는", "is_loses_life_of", "loses life — forward only", "research_metaphor_forward_only"),
            n("히브리서 11:15", "떠나온 땅을 생각하면", "is_think_country_of", "think country — legacy attachment", "research_metaphor_legacy_attachment"),
        ],
    ),
    row(
        "isaac_blessing",
        "이삭 축복 (Isaac Blessing)",
        "창세기 27:27",
        "향기가 에서의 향기 같도다",
        "ANCHOR_GEN_27_27",
        "이삭 축복 은유는 잘못된 배포 대상·권한 오배치 비유이며, 가족이 아님.",
        [
            n("창세기 27:36", "내 이름을 빼앗았도다", "is_stolen_blessing_of", "stolen blessing — wrong tenant", "research_metaphor_wrong_tenant"),
            n("창세기 27:40", "네가 죽을 때에 네 멍에를", "is_break_yoke_of", "break yoke — escape dependency", "research_metaphor_escape_dependency"),
            n("히브리서 11:20", "믿음으로 이삭이 야곱과 에서를", "is_blessed_faith_of", "blessed faith — intended routing", "research_metaphor_intended_routing"),
            n("갈라디아서 4:28", "약속대로 된 이삭과 같으니", "is_like_isaac_of", "like Isaac — legit heir", "research_metaphor_legit_heir"),
        ],
    ),
    row(
        "joseph_coat",
        "요셉 옷 (Joseph Coat)",
        "창세기 37:3",
        "아버지가 그에게 채색 옷을 지어",
        "ANCHOR_GEN_37_3",
        "채색 옷 은유는 특권 플래그·편애된 환경 비유이며, 패션이 아님.",
        [
            n("창세기 37:24", "구덩이에 넣으매", "is_cast_pit_of", "cast pit — sandbox isolation", "research_metaphor_sandbox_isolation"),
            n("창세기 41:41", "온 애굽 땅의 통치자를", "is_ruler_egypt_of", "ruler Egypt — promoted prod", "research_metaphor_promoted_prod"),
            n("창세기 50:20", "당신들은 악을 의도하였으나", "is_meant_evil_good_of", "meant evil good — incident gift", "research_metaphor_incident_gift"),
            n("사도행전 7:9", "하나님이 그와 함께 계시사", "is_god_with_of", "God with — sponsor backup", "research_metaphor_sponsor_backup"),
        ],
    ),
    row(
        "manna_quail",
        "만나 메추라기 (Manna Quail)",
        "출애굽기 16:13",
        "저녁에 메추라기가 와서",
        "ANCHOR_EXO_16_13",
        "만나 메추라기 은유는 일일 배치 공급·쿼터 비유이며, 식량이 아님.",
        [
            n("출애굽기 16:4", "하늘에서 양식을 내려", "is_bread_from_heaven_of", "bread heaven — daily quota", "research_metaphor_daily_quota"),
            n("출애굽기 16:20", "벌레가 들어가 썩더라", "is_worms_bred_of", "worms bred — stale cache", "research_metaphor_stale_cache"),
            n("요한복음 6:31", "하늘에서 떡을 주어", "is_bread_heaven_of", "bread heaven — API ration", "research_metaphor_api_ration"),
            n("고린도전서 10:3", "다 같은 신령한 양식을 먹고", "is_spiritual_food_of", "spiritual food — shared tier", "research_metaphor_shared_tier"),
        ],
    ),
    row(
        "serpent_bronze",
        "놋뱀 (Bronze Serpent)",
        "민수기 21:9",
        "놋뱀을 만들어 기둥 위에",
        "ANCHOR_NUM_21_9",
        "놋뱀 은유는 위험한 핫픽스·바라보면 치유 비유이며, 의료가 아님.",
        [
            n("민수기 21:6", "불뱀이 백성 중에 들어와", "is_fiery_serpents_of", "fiery serpents — outage bites", "research_metaphor_outage_bites"),
            n("요한복음 3:14", "인자가 높이 들려야", "is_son_lifted_of", "Son lifted — public status page", "research_metaphor_public_status_page"),
            n("고린도후서 11:3", "뱀이 그렇게 간교함으로", "is_serpent_deceived_of", "serpent deceived — social eng", "research_metaphor_social_eng"),
            n("요한계시록 12:9", "옛 뱀 곧 마귀", "is_old_serpent_of", "old serpent — legacy debt", "research_metaphor_legacy_debt"),
        ],
    ),
    row(
        "samson_pillars",
        "삼손 기둥 (Samson Pillars)",
        "사사기 16:29",
        "두 기둥의 가운데 기둥을",
        "ANCHOR_JDG_16_29",
        "삼손 기둥 은유는 단일 장애점 붕괴·감당 비용 비유이며, 건축이 아님.",
        [
            n("사사기 16:17", "일곱 땋은 머리털이", "is_seven_locks_of", "seven locks — secret config", "research_metaphor_secret_config"),
            n("사사기 16:20", "여호와께서 자기를 떠나가셨더라", "is_lord_departed_of", "Lord departed — SLO gone", "research_metaphor_slo_gone"),
            n("사사기 16:30", "죽은 자가 나보다 많도다", "is_more_dead_of", "more dead — blast radius", "research_metaphor_blast_radius"),
            n("히브리서 11:32", "기드온과 바락과 삼손과", "is_samson_heroes_of", "Samson heroes — risky hero", "research_metaphor_risky_hero"),
        ],
    ),
    row(
        "elisha_axe_float",
        "엘리사 도끼 뜸 (Elisha Axe Float)",
        "열왕기하 6:6",
        "나무를 던지매 쇠가 떠올랐더라",
        "ANCHOR_2KI_6_6",
        "도끼 뜸 은유는 침수된 자산 복구·비용 회수 비유이며, 공구가 아님.",
        [
            n("열왕기하 6:5", "도끼 머리가 물에 떨어지매", "is_axe_head_fell_of", "axe head fell — sunk cost", "research_metaphor_sunk_cost"),
            n("열왕기하 6:7", "쇠가 떠오르니", "is_iron_swam_of", "iron swam — recovered asset", "research_metaphor_recovered_asset"),
            n("시편 124:3", "우리를 삼키지 아니하였고", "is_not_swallowed_of", "not swallowed — narrow escape", "research_metaphor_narrow_escape"),
            n("마태복음 14:31", "물 위로 걸어오다가", "is_walked_water_of", "walked water — improbable fix", "research_metaphor_improbable_fix"),
        ],
    ),
    row(
        "belshazzar_feast",
        "벨사살 잔치 (Belshazzar Feast)",
        "다니엘 5:5",
        "왕궁 취벽에 사람의 손가락이 나타나",
        "ANCHOR_DAN_5_5",
        "벨사살 잔치 은유는 무시된 경고·감사 로그 비유이며, 연회가 아님.",
        [
            n("다니엘 5:25", "메네 메네 데겔 우바르신", "is_mene_tekel_of", "mene tekel — written verdict", "research_metaphor_written_verdict"),
            n("다니엘 5:30", "그 밤에 갈대아 사람 벨사살 왕이", "is_slain_night_of", "slain night — same-day breach", "research_metaphor_same_day_breach"),
            n("잠언 23:29", "누구에게 화가 있으며", "is_woe_strong_of", "woe strong drink — ignore alerts", "research_metaphor_ignore_alerts"),
            n("누가복음 12:20", "어리석은 자여 오늘 밤", "is_fool_tonight_of", "fool tonight — no DR plan", "research_metaphor_no_dr_plan"),
        ],
    ),
    row(
        "cyrus_decree",
        "고레스 조서 (Cyrus Decree)",
        "에스라 1:2",
        "하나님의 전을 예루살렘에서 건축하게 하라",
        "ANCHOR_EZR_1_2",
        "고레스 조서 은유는 상위 정책·규제 면제 비유이며, 역사가 아님.",
        [
            n("이사야 44:28", "예루살렘을 건축하게 하며", "is_rebuild_jerusalem_of", "rebuild Jerusalem — greenfield mandate", "research_metaphor_greenfield_mandate"),
            n("에스라 6:14", "아닥사스다 왕의 명령을 따라", "is_king_decree_of", "king decree — exec memo", "research_metaphor_exec_memo"),
            n("에스겔 37:21", "내가 그들을 취하여", "is_gather_israel_of", "gather Israel — reunify cluster", "research_metaphor_reunify_cluster"),
            n("로마서 13:1", "높은 권세는 하나님께로부터", "is_authorities_god_of", "authorities God — compliance top", "research_metaphor_compliance_top"),
        ],
    ),
    row(
        "esther_queen",
        "에스더 왕후 (Esther Queen)",
        "에스더 2:17",
        "왕이 에스더를 더 사랑하므로",
        "ANCHOR_EST_2_17",
        "에스더 왕후 은유는 내부 챔피언·스폰서십 비유이며, 왕실이 아님.",
        [
            n("에스더 4:14", "왕궁에 이르러", "is_royal_position_of", "royal position — insider role", "research_metaphor_insider_role"),
            n("에스더 7:3", "내 생명을 구하여 주시고", "is_plead_life_of", "plead life — escalate P0", "research_metaphor_escalate_p0"),
            n("에스더 8:17", "유다인에게 기쁨과 즐거움", "is_joy_jews_of", "joy Jews — team relief", "research_metaphor_team_relief"),
            n("잠언 31:10", "현숙한 여인을 누가 찾을 수 있으랴", "is_virtuous_wife_of", "virtuous wife — rare talent", "research_metaphor_rare_talent"),
        ],
    ),
    row(
        "haman_gallows",
        "하만 나무 (Haman Gallows)",
        "에스더 7:10",
        "하만이 모르드개를 위하여 세운",
        "ANCHOR_EST_7_10",
        "하만 나무 은유는 자기 함정·악의 스크립트 역류 비유이며, 형벌이 아님.",
        [
            n("에스더 5:14", "오십 규빗 높은 나무를", "is_gallows_fifty_of", "gallows fifty — overbuilt trap", "research_metaphor_overbuilt_trap"),
            n("에스더 6:4", "왕궁 문 앞에 있는 하만이", "is_haman_court_of", "Haman court — waiting attacker", "research_metaphor_waiting_attacker"),
            n("잠언 26:27", "구덩이를 파는 자는", "is_digs_pit_of", "digs pit — own exploit", "research_metaphor_own_exploit"),
            n("갈라디아서 6:7", "자기의 심은 대로 거두리라", "is_reap_sow_of", "reap sow — karma deploy", "research_metaphor_karma_deploy"),
        ],
    ),
]


def main() -> int:
    slugs: set[str] = set()
    for path in DB.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    existing_seed: set[str] = set()
    if APPEND.is_file():
        for line in APPEND.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_seed.add(json.loads(line).get("slug", ""))
    added = 0
    with APPEND.open("a", encoding="utf-8") as fh:
        for r in NEW:
            if r["slug"] in slugs or r["slug"] in existing_seed:
                continue
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            added += 1
    print(f"appended {added} seeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
