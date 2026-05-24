#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v8, Track B NON_GATING)."""
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
        "peter_walk_water",
        "베드로 물위 걸음 (Peter Walk Water)",
        "마태복음 14:29",
        "물 위로 걸어와 예수께로",
        "ANCHOR_MAT_14_29",
        "물위 걸음 은유는 과신한 배포·SRE 실험 비유이며, 수영이 아님.",
        [
            n("마태복음 14:30", "바람을 보고 두려워하여", "is_saw_wind_afraid_of", "saw wind afraid — metric spike fear", "research_metaphor_metric_spike_fear"),
            n("마태복음 14:31", "손을 내미사 붙잡으시고", "is_reached_hand_of", "reached hand — rollback assist", "research_metaphor_rollback_assist"),
            n("요한복음 21:7", "베드로가 옷을 두르고", "is_peter_clothed_of", "Peter clothed — dress for prod", "research_metaphor_dress_for_prod"),
            n("히브리서 11:29", "홍해를 마른 땅과 같이", "is_sea_dry_faith_of", "sea dry faith — impossible path", "research_metaphor_impossible_path"),
        ],
    ),
    row(
        "pentecost_wind",
        "오순절 바람 (Pentecost Wind)",
        "사도행전 2:2",
        "하늘로부터 급하고 강한 바람 같은 소리가",
        "ANCHOR_ACT_2_2",
        "오순절 바람 은유는 대규모 이벤트 버스트·팬아웃 비유이며, 기상이 아님.",
        [
            n("사도행전 2:3", "혀같이 갈라지는 것들이", "is_tongues_fire_of", "tongues fire — multi-region deploy", "research_metaphor_multi_region_deploy"),
            n("사도행전 2:4", "성령의 충만함을 받아", "is_filled_spirit_of", "filled spirit — team sync", "research_metaphor_team_sync"),
            n("요엘 2:28", "내가 내 영을 모든 육체에게 부어", "is_pour_spirit_of", "pour spirit — broadcast config", "research_metaphor_broadcast_config"),
            n("고린도전서 12:7", "성령의 나타남은 각 사람에게", "is_manifestation_spirit_of", "manifestation spirit — per-node gift", "research_metaphor_per_node_gift"),
        ],
    ),
    row(
        "stephen_stones",
        "스데반 돌 (Stephen Stones)",
        "사도행전 7:59",
        "돌을 들어 스데반을 쳐",
        "ANCHOR_ACT_7_59",
        "스데반 돌 은유는 내부 고발·치명적 리뷰 비유이며, 폭력이 아님.",
        [
            n("사도행전 6:5", "믿음과 성령이 충만한", "is_full_faith_of", "full faith — trusted reviewer", "research_metaphor_trusted_reviewer"),
            n("사도행전 7:55", "하늘이 열리고", "is_heaven_opened_of", "heaven opened — full trace view", "research_metaphor_full_trace_view"),
            n("사도행전 8:1", "사울이 그의 죽임을 좋게 여기니", "is_saul_approved_of", "Saul approved — hostile stakeholder", "research_metaphor_hostile_stakeholder"),
            n("히브리서 11:37", "돌로 치는 것과 톱으로 켜는", "is_stoned_sawn_of", "stoned sawn — harsh audit", "research_metaphor_harsh_audit"),
        ],
    ),
    row(
        "philip_ethiopian",
        "빌립 에티오피아 (Philip Ethiopian)",
        "사도행전 8:35",
        "이사야의 글을 가리켜",
        "ANCHOR_ACT_8_35",
        "빌립 은유는 온보딩·문서 해석 멘토 비유이며, 선교가 아님.",
        [
            n("사도행전 8:26", "가사에로 가는 길로", "is_road_gaza_of", "road Gaza — edge route", "research_metaphor_edge_route"),
            n("사도행전 8:30", "이 글을 네가 깨달으니이까", "is_understand_reading_of", "understand reading — parse SSOT", "research_metaphor_parse_ssot"),
            n("사도행전 8:38", "물 가운데서 빌립과 함께", "is_baptized_water_of", "baptized water — certify user", "research_metaphor_certify_user"),
            n("이사야 53:7", "도살장으로 끌려가는 어린 양", "is_lamb_slaughter_of", "lamb slaughter — sacrifice narrative", "research_metaphor_sacrifice_narrative"),
        ],
    ),
    row(
        "prison_earthquake",
        "옥중 지진 (Prison Earthquake)",
        "사도행전 16:26",
        "홀연히 큰 지진이 나서",
        "ANCHOR_ACT_16_26",
        "옥 지진 은유는 장애로 잠금 해제·우연한 복구 비유이며, 지진학이 아님.",
        [
            n("사도행전 16:25", "밤중쯤 되어 기도하고", "is_prayed_sang_of", "prayed sang — night maintenance", "research_metaphor_night_maintenance"),
            n("사도행전 16:27", "간수가 잠에서 깨어나", "is_jailer_woke_of", "jailer woke — on-call paged", "research_metaphor_oncall_paged"),
            n("사도행전 16:34", "온 집안이 하나님을 믿으니", "is_household_believed_of", "household believed — team buy-in", "research_metaphor_team_buy_in"),
            n("시편 79:11", "죽기 직전한 자의 몸을 기억하소서", "is_remember_prisoners_of", "remember prisoners — stuck tickets", "research_metaphor_stuck_tickets"),
        ],
    ),
    row(
        "shipwreck_paul",
        "바울 난파 (Paul Shipwreck)",
        "사도행전 27:41",
        "배가 걸리고 고정하여",
        "ANCHOR_ACT_27_41",
        "난파 은유는 프로젝트 전면 중단·부분 생존 비유이며, 해운이 아님.",
        [
            n("사도행전 27:22", "내가 너희 가운데서", "is_angel_stood_of", "angel stood — exec assurance", "research_metaphor_exec_assurance"),
            n("사도행전 27:31", "이 사람들이 배에 머물지 아니하면", "is_stay_ship_of", "stay ship — keep core service", "research_metaphor_keep_core_service"),
            n("사도행전 28:2", "비가 내리고 날이 차매", "is_rain_cold_of", "rain cold — post-incident chill", "research_metaphor_post_incident_chill"),
            n("고린도후서 11:25", "세 번 파선하고", "is_three_shipwrecks_of", "three shipwrecks — veteran SRE", "research_metaphor_veteran_sre"),
        ],
    ),
    row(
        "thorn_flesh",
        "바울 가시 (Paul Thorn)",
        "고린도후서 12:7",
        "내 육체에 가시를 주사",
        "ANCHOR_2CO_12_7",
        "가시 은유는 만성 장애·완치 불가 버그 비유이며, 질병이 아님.",
        [
            n("고린도후서 12:9", "내 은혜가 네게 족하도다", "is_grace_sufficient_of", "grace sufficient — work around", "research_metaphor_work_around"),
            n("고린도후서 12:10", "약한 것을 자랑하리니", "is_boast_weaknesses_of", "boast weaknesses — honest postmortem", "research_metaphor_honest_postmortem"),
            n("갈라디아서 4:13", "육체의 약함으로", "is_infirmity_flesh_of", "infirmity flesh — chronic debt", "research_metaphor_chronic_debt"),
            n("빌립보서 4:12", "비천에도 있고 부하게도", "is_abased_abound_of", "abased abound — variable load", "research_metaphor_variable_load"),
        ],
    ),
    row(
        "armor_god",
        "하나님의 갑옷 (Armor of God)",
        "에베소서 6:11",
        "마귀의 간계를 능히 대적하기 위하여",
        "ANCHOR_EPH_6_11",
        "갑옷 은유는 보안 레이어·방어 체크리스트 비유이며, 군사가 아님.",
        [
            n("에베소서 6:14", "진리로 너희 허리띠를", "is_belt_truth_of", "belt truth — config baseline", "research_metaphor_config_baseline"),
            n("에베소서 6:16", "믿음의 방패로", "is_shield_faith_of", "shield faith — WAF layer", "research_metaphor_waf_layer"),
            n("에베소서 6:17", "구원의 투구와", "is_helmet_salvation_of", "helmet salvation — backup restore", "research_metaphor_backup_restore"),
            n("로마서 13:12", "어두움의 일을 벗어버리고", "is_cast_off_darkness_of", "cast off darkness — patch CVE", "research_metaphor_patch_cve"),
        ],
    ),
    row(
        "ruth_glean",
        "룻 이삭 줍기 (Ruth Glean)",
        "룻기 2:2",
        "이삭을 이을 자가 있으면",
        "ANCHOR_RUT_2_2",
        "이삭 줍기 은유는 잔여 리소스·스크랩 수집 비유이며, 농업이 아님.",
        [
            n("룻기 2:10", "어찌하여 내게 은혜를 베푸시나이까", "is_why_favor_of", "why favor — unexpected quota", "research_metaphor_unexpected_quota"),
            n("룻기 2:16", "그녀에게 조금씩 떨어뜨려", "is_drop_handfuls_of", "drop handfuls — intentional slack", "research_metaphor_intentional_slack"),
            n("룻기 3:15", "겉옷을 잡으라", "is_hold_garment_of", "hold garment — claim resource", "research_metaphor_claim_resource"),
            n("레위기 19:9", "밭 이삭의 모퉁이를", "is_corner_field_of", "corner field — reserved buffer", "research_metaphor_reserved_buffer"),
        ],
    ),
    row(
        "hannah_prayer",
        "한나 기도 (Hannah Prayer)",
        "사무엘상 1:10",
        "여호와 앞에서 통곡하며",
        "ANCHOR_1SA_1_10",
        "한나 기도 은유는 장기 티켓·끈질긴 에스컬레이션 비유이며, 종교가 아님.",
        [
            n("사무엘상 1:11", "만일 주의 여종에게", "is_vow_if_of", "vow if — SLA pledge", "research_metaphor_sla_pledge"),
            n("사무엘상 1:20", "한나가 임신하여 아들을 낳으매", "is_bore_samuel_of", "bore Samuel — deliverable born", "research_metaphor_deliverable_born"),
            n("사무엘상 2:1", "내 마음이 여호와로 말미암아", "is_rejoices_lord_of", "rejoices Lord — closure joy", "research_metaphor_closure_joy"),
            n("누가복음 1:46", "내 영혼이 주를 기뻐하며", "is_magnifies_soul_of", "magnifies soul — celebrate ship", "research_metaphor_celebrate_ship"),
        ],
    ),
    row(
        "eli_lamp",
        "엘리 등불 (Eli Lamp)",
        "사무엘상 3:3",
        "하나님의 등불이 아직 꺼지지 아니하였고",
        "ANCHOR_1SA_3_3",
        "엘리 등불 은유는 레거시 모니터·거의 꺼진 알람 비유이며, 조명이 아님.",
        [
            n("사무엘상 3:10", "사무엘이 여호와여 말씀하시옵소서", "is_speak_lord_of", "speak Lord — ack page", "research_metaphor_ack_page"),
            n("사무엘상 4:18", "이스라엘의 영광이", "is_glory_departed_of", "glory departed — major outage", "research_metaphor_major_outage"),
            n("마태복음 25:8", "등불이 꺼져가니", "is_lamps_going_out_of", "lamps going out — battery drain", "research_metaphor_battery_drain"),
            n("잠언 20:27", "여호와의 등불은 사람의 영혼이라", "is_lamp_lord_of", "lamp Lord — inner metric", "research_metaphor_inner_metric"),
        ],
    ),
    row(
        "census_david",
        "다윗 인구 조사 (David Census)",
        "역대상 21:1",
        "사탄이 일어나 이스라엘을 대적하여",
        "ANCHOR_1CH_21_1",
        "인구 조사 은유는 불필요한 전수 스캔·비용 폭탄 비유이며, 인구통계가 아님.",
        [
            n("역대상 21:7", "이 일이 하나님 보시기에", "is_displeased_god_of", "displeased God — policy violation", "research_metaphor_policy_violation"),
            n("사무엘하 24:25", "다윗이 그 곳에서", "is_built_altar_of", "built altar — pay penalty", "research_metaphor_pay_penalty"),
            n("출애굽기 30:12", "각 사람이 여호와께 속죄 헌물을", "is_ransom_soul_of", "ransom soul — per-head fee", "research_metaphor_per_head_fee"),
            n("민수기 1:49", "레위 지파는 조사하지 말지니", "is_levi_not_counted_of", "Levi not counted — exempt class", "research_metaphor_exempt_class"),
        ],
    ),
    row(
        "uriah_letter",
        "우리아 편지 (Uriah Letter)",
        "사무엘하 11:15",
        "요압의 손에 주어 우리아를",
        "ANCHOR_2SA_11_15",
        "우리아 편지 은유는 악의적 라우팅·희생자 배포 비유이며, 우편이 아님.",
        [
            n("사무엘하 11:11", "어찌 내 주 왕의 신복들이", "is_siege_camp_of", "siege camp — frontline duty", "research_metaphor_frontline_duty"),
            n("사무엘하 12:7", "네가 그 사람을 죽였도다", "is_you_killed_of", "you killed — blame assigned", "research_metaphor_blame_assigned"),
            n("잠언 6:16", "여호와께서 미워하시는", "is_hates_lying_of", "hates lying — ethics breach", "research_metaphor_ethics_breach"),
            n("야고보서 1:14", "각 사람이 시험을 받는 것은", "is_tempted_lust_of", "tempted lust — shortcut urge", "research_metaphor_shortcut_urge"),
        ],
    ),
    row(
        "bathsheba_roof",
        "밧세바 지붕 (Bathsheba Roof)",
        "사무엘하 11:2",
        "지붕에서 한 여인을 목욕하는 것을",
        "ANCHOR_2SA_11_2",
        "지붕 은유는 프라이버시 침해·관측 과잉 비유이며, 스캔들이 아님.",
        [
            n("사무엘하 11:4", "다윗이 사자를 보내어", "is_sent_messengers_of", "sent messengers — overreach API", "research_metaphor_overreach_api"),
            n("사무엘하 12:9", "어찌하여 여호와의 일을", "is_despised_word_of", "despised word — ignore policy", "research_metaphor_ignore_policy"),
            n("시편 51:1", "하나님이여 주의 인자하심을", "is_mercy_blot_of", "mercy blot — incident repent", "research_metaphor_incident_repent"),
            n("마태복음 5:28", "이미 마음에 음욕을 품한 자는", "is_lust_heart_of", "lust heart — intent log", "research_metaphor_intent_log"),
        ],
    ),
    row(
        "nathan_parable",
        "나단 우화 (Nathan Parable)",
        "사무엘하 12:1",
        "두 사람이 한 성에 살았는데",
        "ANCHOR_2SA_12_1",
        "나단 우화 은유는 간접 감사·메타포 리뷰 비유이며, 소설이 아님.",
        [
            n("사무엘하 12:7", "네가 그 사람을 죽였도다", "is_you_are_man_of", "you are man — mirror finding", "research_metaphor_mirror_finding"),
            n("사무엘하 12:13", "내가 여호와께 범죄하였나이다", "is_sinned_lord_of", "sinned Lord — admit fault", "research_metaphor_admit_fault"),
            n("누가복음 15:11", "어떤 사람이 두 아들을", "is_prodigal_son_of", "prodigal son — drift story", "research_metaphor_drift_story"),
            n("이사야 5:1", "내가 나의 사랑하는 자를 위하여", "is_song_vineyard_of", "song vineyard — case study", "research_metaphor_case_study"),
        ],
    ),
    row(
        "queen_sheba",
        "시바 여왕 (Queen of Sheba)",
        "열왕기상 10:2",
        "매우 많은 선물을 가지고",
        "ANCHOR_1KI_10_2",
        "시바 여왕 은유는 외부 벤치마크·감사 방문 비유이며, 외교가 아님.",
        [
            n("열왕기상 10:7", "내가 듣지 못한 것을", "is_not_half_told_of", "not half told — hype exceeded", "research_metaphor_hype_exceeded"),
            n("열왕기상 10:9", "이스라엘을 다스리게 하시려고", "is_loved_israel_of", "loved Israel — sponsor nation", "research_metaphor_sponsor_nation"),
            n("마태복음 12:42", "남방 여왕이 일어나", "is_queen_south_of", "queen south — external audit", "research_metaphor_external_audit"),
            n("잠언 25:2", "왕의 일은 하나님께 속하나", "is_king_glory_of", "king glory — opaque ops", "research_metaphor_opaque_ops"),
        ],
    ),
    row(
        "widow_zarephath",
        "사렙다 과부 (Widow Zarephath)",
        "열왕기상 17:12",
        "나와 내 아들은 먹고 죽기를",
        "ANCHOR_1KI_17_12",
        "사렙다 과부 은유는 마지막 쿼터·비상 버퍼 비유이며, 가난이 아님.",
        [
            n("열왕기상 17:14", "가루통의 가루가 다하지 아니하며", "is_flour_not_fail_of", "flour not fail — miracle quota", "research_metaphor_miracle_quota"),
            n("열왕기상 17:22", "여호와의 말씀이 엘리야에게", "is_soul_returned_of", "soul returned — revive service", "research_metaphor_revive_service"),
            n("누가복음 4:26", "엘리야가 사렙다에", "is_sent_elijah_of", "sent Elijah — edge site", "research_metaphor_edge_site"),
            n("마가복음 12:43", "가난한 과부가", "is_widow_mite_of", "widow mite — all-in budget", "research_metaphor_all_in_budget"),
        ],
    ),
    row(
        "gehazi_greed",
        "게하시 탐욕 (Gehazi Greed)",
        "열왕기하 5:27",
        "나아만의 문둥병이 네게 들리고",
        "ANCHOR_2KI_5_27",
        "게하시 은유는 권한 남용·비밀 수수 비유이며, 질병이 아님.",
        [
            n("열왕기하 5:20", "내 주인이 이 아람 사람 나아만을", "is_gehazi_ran_of", "Gehazi ran — shadow billing", "research_metaphor_shadow_billing"),
            n("열왕기하 5:26", "내 마음이 너와 함께 있지 아니하였느냐", "is_not_go_with_of", "not go with — audit trail gap", "research_metaphor_audit_trail_gap"),
            n("디모데후서 6:10", "돈을 사랑함이 일만 악의 뿌리가", "is_love_money_of", "love money — incentive skew", "research_metaphor_incentive_skew"),
            n("잠언 15:27", "이익을 좋아하는 자는", "is_greedy_gain_of", "greedy gain — quota gaming", "research_metaphor_quota_gaming"),
        ],
    ),
    row(
        "lazarus_tomb",
        "나사로 무덤 (Lazarus Tomb)",
        "요한복음 11:43",
        "나사로야 나오라 하시니",
        "ANCHOR_JHN_11_43",
        "나사로 무덤 은유는 장기 다운 서비스 복구·대기 후 기동 비유이며, 부활 신학 단정 아님.",
        [
            n("요한복음 11:35", "예수께서 눈물을 흘리시더라", "is_jesus_wept_of", "Jesus wept — empathetic RCA", "research_metaphor_empathetic_rca"),
            n("요한복음 11:39", "벌써 냄새가 나나이다", "is_already_stinks_of", "already stinks — stale data", "research_metaphor_stale_data"),
            n("요한복음 11:44", "수북에 쌓인 자가", "is_came_forth_of", "came forth — cold start OK", "research_metaphor_cold_start_ok"),
            n("히브리서 11:19", "죽은 자 가운데서 다시 살리실 줄", "is_raise_dead_of", "raise dead — DR drill", "research_metaphor_dr_drill"),
        ],
    ),
    row(
        "road_emmaus",
        "엠마오 길 (Road Emmaus)",
        "누가복음 24:15",
        "길을 가면서 서로 이야기할 때에",
        "ANCHOR_LUK_24_15",
        "엠마오 길 은유는 사후 복기·페어링 워크스루 비유이며, 순례이 아님.",
        [
            n("누가복음 24:27", "모세와 모든 선지자에게", "is_expounded_scriptures_of", "expounded scriptures — read logs", "research_metaphor_read_logs"),
            n("누가복음 24:31", "그들의 눈이 밝아져", "is_eyes_opened_of", "eyes opened — root cause seen", "research_metaphor_root_cause_seen"),
            n("누가복음 24:32", "길에서 우리에게 말씀하시고", "is_burned_hearts_of", "burned hearts — aha moment", "research_metaphor_aha_moment"),
            n("시편 119:105", "주의 말씀은 내 발에 등이요", "is_lamp_feet_of", "lamp feet — runbook light", "research_metaphor_runbook_light"),
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
