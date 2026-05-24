#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v9, Track B NON_GATING)."""
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
        "judas_betrayal",
        "유다 배반 (Judas Betrayal)",
        "마태복음 26:48",
        "예수님께 입맞추라",
        "ANCHOR_MAT_26_48",
        "유다 배반 은유는 내부자 키 유출·트레이터 턴 비유이며, 종교 논쟁이 아님.",
        [
            n("마태복음 26:15", "은 삼십을 주고", "is_thirty_silver_of", "thirty silver — bounty price", "research_metaphor_bounty_price"),
            n("마태복음 27:3", "보고 뉘우쳐 은을", "is_repented_returned_of", "repented returned — tried rollback", "research_metaphor_tried_rollback"),
            n("요한복음 13:27", "사탄이 그에게 들어가시니", "is_satan_entered_of", "Satan entered — compromised account", "research_metaphor_compromised_account"),
            n("시편 41:9", "나를 먹던 자가", "is_ate_bread_of", "ate bread — trusted insider", "research_metaphor_trusted_insider"),
        ],
    ),
    row(
        "thirty_pieces",
        "은 삼십 (Thirty Pieces Silver)",
        "마태복음 27:3",
        "은 삼십을 대제사장들에게",
        "ANCHOR_MAT_27_3",
        "은 삼십 은유는 손실 한도·배상 상한 비유이며, 화폐가 아님.",
        [
            n("스가랴 11:12", "그들이 내 고가 은 삼십을", "is_thirty_silver_price_of", "thirty silver price — fixed payout", "research_metaphor_fixed_payout"),
            n("마태복음 26:15", "은 삼십을 주고", "is_weighed_out_of", "weighed out — contract price", "research_metaphor_contract_price"),
            n("출애굽기 21:32", "소나 어린 양을 친 자에게", "is_thirty_shekels_of", "thirty shekels — liability cap", "research_metaphor_liability_cap"),
            n("잠언 11:4", "재물은 진노의 날에", "is_riches_no_profit_of", "riches no profit — wrong incentive", "research_metaphor_wrong_incentive"),
        ],
    ),
    row(
        "cock_crow",
        "닭 울음 (Cock Crow)",
        "마태복음 26:74",
        "닭이 울기 전에 네가 세 번",
        "ANCHOR_MAT_26_74",
        "닭 울음 은유는 SLA 위반 알람·예측된 실패 비유이며, 가금이 아님.",
        [
            n("마태복음 26:34", "이 밤에 닭 울기 전에", "is_before_cock_of", "before cock — deadline known", "research_metaphor_deadline_known"),
            n("마태복음 26:75", "베드로가 예수의 말씀을", "is_remembered_words_of", "remembered words — alert fired", "research_metaphor_alert_fired"),
            n("누가복음 22:61", "주께서 돌이키사 베드로를", "is_lord_turned_of", "Lord turned — dashboard stare", "research_metaphor_dashboard_stare"),
            n("고린도전서 10:12", "선을 줄로 생각하는 너는", "is_thinks_stands_of", "thinks stands — overconfidence", "research_metaphor_overconfidence"),
        ],
    ),
    row(
        "barabbas_release",
        "바라바 석방 (Barabbas Release)",
        "마태복음 27:21",
        "바라바를 놓아 주기를 원하느냐",
        "ANCHOR_MAT_27_21",
        "바라바 석방 은유는 잘못된 A/B 선택·군중 우선순위 비유이며, 형사가 아님.",
        [
            n("마태복음 27:16", "감옥에 갇혀 있는 유명한 죄수", "is_notorious_prisoner_of", "notorious prisoner — known bad build", "research_metaphor_known_bad_build"),
            n("마태복음 27:26", "바라바는 놓아 주고", "is_released_barabbas_of", "released Barabbas — wrong winner", "research_metaphor_wrong_winner"),
            n("요한복음 18:40", "우리는 이 사람이 아니요", "is_not_this_man_of", "not this man — reject fix", "research_metaphor_reject_fix"),
            n("잠언 14:12", "그 끝은 사망의 길이니라", "is_way_seems_right_of", "way seems right — bad default", "research_metaphor_bad_default"),
        ],
    ),
    row(
        "veil_torn",
        "휘장 찢김 (Veil Torn)",
        "마태복음 27:51",
        "성소의 휘장이 위에서 아래까지",
        "ANCHOR_MAT_27_51",
        "휘장 찢김 은유는 권한 경계 제거·관측 가능화 비유이며, 직물이 아님.",
        [
            n("히브리서 10:20", "새롭고 산 길을", "is_new_living_way_of", "new living way — new API path", "research_metaphor_new_api_path"),
            n("히브리서 9:8", "첫 장막이 아직 서 있는 동안에는", "is_first_tabernacle_of", "first tabernacle — old gateway", "research_metaphor_old_gateway"),
            n("마가복음 15:38", "휘장이 둘로 찢어져", "is_veil_torn_of", "veil torn — firewall down", "research_metaphor_firewall_down"),
            n("에베소서 2:14", "우리 가운데 막힌 담을", "is_broken_down_wall_of", "broken down wall — removed ACL", "research_metaphor_removed_acl"),
        ],
    ),
    row(
        "empty_tomb",
        "빈 무덤 (Empty Tomb)",
        "마태복음 28:6",
        "여기 계시지 않고",
        "ANCHOR_MAT_28_6",
        "빈 무덤 은유는 예상 상태 불일치·무결성 검증 비유이며, 신학 단정 아님.",
        [
            n("마태복음 28:4", "파수꾼들이 무서워하여", "is_guards_shook_of", "guards shook — on-call panic", "research_metaphor_oncall_panic"),
            n("누가복음 24:3", "들어가도 주의 시체를", "is_body_not_found_of", "body not found — 404 expected", "research_metaphor_404_expected"),
            n("요한복음 20:8", "보고 믿으니라", "is_saw_believed_of", "saw believed — evidence accepted", "research_metaphor_evidence_accepted"),
            n("고린도전서 15:14", "만일 그리스도께서", "is_if_not_raised_of", "if not raised — hypothesis fail", "research_metaphor_hypothesis_fail"),
        ],
    ),
    row(
        "doubting_thomas",
        "도마 의심 (Doubting Thomas)",
        "요한복음 20:25",
        "내 손가락을 그 못 자국에",
        "ANCHOR_JHN_20_25",
        "도마 의심 은유는 실측 요구·재현 증거 비유이며, 신앙 논쟁이 아님.",
        [
            n("요한복음 20:27", "네 손가락을 이리 내밀어", "is_reach_hand_of", "reach hand — hands-on verify", "research_metaphor_hands_on_verify"),
            n("요한복음 20:29", "보고 믿는 자들은", "is_blessed_not_seen_of", "blessed not seen — trust CI", "research_metaphor_trust_ci"),
            n("히브리서 11:1", "바라는 것들의 실상이요", "is_faith_substance_of", "faith substance — hypothesis", "research_metaphor_hypothesis"),
            n("야고보서 1:6", "믿음에 조금도 의심하지 말라", "is_doubt_not_of", "doubt not — flaky test", "research_metaphor_flaky_test"),
        ],
    ),
    row(
        "saul_road",
        "사울 다메섹 길 (Saul Road)",
        "사도행전 9:3",
        "해가 한낮보다 더 밝게",
        "ANCHOR_ACT_9_3",
        "다메섹 길 은유는 강제 피벗·아키텍처 전환 비유이며, 순례이 아님.",
        [
            n("사도행전 9:4", "사울아 사울아", "is_saul_saul_of", "Saul Saul — hard stop", "research_metaphor_hard_stop"),
            n("사도행전 9:9", "사흘 동안 눈이 보이지 아니하고", "is_three_days_blind_of", "three days blind — outage window", "research_metaphor_outage_window"),
            n("갈라디아서 1:15", "모태로부터 나를 택정하시고", "is_called_grace_of", "called grace — reorg mandate", "research_metaphor_reorg_mandate"),
            n("빌립보서 3:6", "율법의 의에 있어서", "is_blameless_law_of", "blameless law — old KPI perfect", "research_metaphor_old_kpi_perfect"),
        ],
    ),
    row(
        "lystra_stones",
        "루스드라 돌 (Lystra Stones)",
        "사도행전 14:19",
        "돌을 들어 바울에게 던져",
        "ANCHOR_ACT_14_19",
        "루스드라 돌 은유는 현장 거부·롤백 실패 비유이며, 폭력이 아님.",
        [
            n("사도행전 14:11", "신들이 사람의 형상으로", "is_gods_men_of", "gods men — misread metrics", "research_metaphor_misread_metrics"),
            n("사도행전 14:15", "헛된 일을 그치고", "is_turn_vain_of", "turn vain — stop vanity deploy", "research_metaphor_stop_vanity_deploy"),
            n("고린도후서 11:25", "한 번 돌에 맞음을", "is_stoned_once_of", "stoned once — hostile region", "research_metaphor_hostile_region"),
            n("잠언 26:11", "개가 그 토한 것을", "is_dog_vomit_of", "dog vomit — repeat mistake", "research_metaphor_repeat_mistake"),
        ],
    ),
    row(
        "boaz_redeemer",
        "보아스 구속자 (Boaz Redeemer)",
        "룻기 4:9",
        "보아스가 장로들과 모든 백성에게",
        "ANCHOR_RUT_4_9",
        "구속자 은유는 기술 부채 상환·인수 합병 비유이며, 가족법이 아님.",
        [
            n("룻기 4:6", "내가 나를 해할까 하노라", "is_mar_redemption_of", "mar redemption — decline scope", "research_metaphor_decline_scope"),
            n("룻기 4:10", "나보다 더 가까운 자가 있으나", "is_nearer_kinsman_of", "nearer kinsman — prior claim", "research_metaphor_prior_claim"),
            n("갈라디아서 3:13", "그리스도께서 우리를 위하여", "is_redeemed_curse_of", "redeemed curse — paid debt", "research_metaphor_paid_debt"),
            n("레위기 25:25", "그의 가까운 친족이", "is_kinsman_redeem_of", "kinsman redeem — maintainer on-call", "research_metaphor_maintainer_oncall"),
        ],
    ),
    row(
        "moses_tablets",
        "모세 두 돌판 (Moses Tablets)",
        "출애굽기 32:19",
        "손에서 내려 땅에 던져",
        "ANCHOR_EXO_32_19",
        "돌판 은유는 계약 파기·스키마 폐기 비유이며, 조각상이 아님.",
        [
            n("출애굽기 31:18", "돌판을 쓰시고", "is_tablets_written_of", "tablets written — signed contract", "research_metaphor_signed_contract"),
            n("출애굽기 32:8", "금송아지를 부어", "is_golden_calf_of", "golden calf — rogue deploy", "research_metaphor_rogue_deploy"),
            n("출애굽기 34:1", "첫 돌판과 같은 돌판을", "is_new_tablets_of", "new tablets — v2 schema", "research_metaphor_v2_schema"),
            n("고린도후서 3:6", "글자는 죽이고", "is_letter_kills_of", "letter kills — rigid policy", "research_metaphor_rigid_policy"),
        ],
    ),
    row(
        "jephthah_vow",
        "입다 서원 (Jephthah Vow)",
        "사사기 11:30",
        "만일 주께서 암몬 자손을",
        "ANCHOR_JDG_11_30",
        "입다 서원 은유는 과도한 SLA 약속·되돌릴 수 없는 배포 비유이며, 가족이 아님.",
        [
            n("사사기 11:35", "내 입을 여호와께로 열었으므로", "is_opened_mouth_of", "opened mouth — committed flag", "research_metaphor_committed_flag"),
            n("사사기 11:39", "딸이 돌아오매", "is_daughter_returned_of", "daughter returned — costly win", "research_metaphor_costly_win"),
            n("잠언 20:25", "말씀 없이 성물을 구별하는 것은", "is_rash_vow_of", "rash vow — no rollback", "research_metaphor_no_rollback"),
            n("전도서 5:4", "서원을 갚는 것보다", "is_pay_vow_of", "pay vow — honor debt", "research_metaphor_honor_debt"),
        ],
    ),
    row(
        "ehud_dagger",
        "에훗 단검 (Ehud Dagger)",
        "사사기 3:21",
        "오른손으로 단검을 빼어",
        "ANCHOR_JDG_3_21",
        "에훗 단검 은유는 좁은 침투·내부 제거 비유이며, 무기가 아님.",
        [
            n("사사기 3:15", "왼손잡이 에훗이라", "is_left_handed_of", "left handed — unconventional path", "research_metaphor_unconventional_path"),
            n("사사기 3:30", "모압이 그 날에 이스라엘의 손에", "is_moab_subdued_of", "Moab subdued — incident closed", "research_metaphor_incident_closed"),
            n("히브리서 4:12", "하나님의 말씀은 살아 있고", "is_sword_spirit_of", "sword spirit — sharp patch", "research_metaphor_sharp_patch"),
            n("에베소서 6:17", "성령의 검 곧", "is_sword_spirit_word_of", "sword spirit word — precise fix", "research_metaphor_precise_fix"),
        ],
    ),
    row(
        "deborah_palm",
        "드보라 종려나무 (Deborah Palm)",
        "사사기 4:5",
        "에브라임 산지 라비딧의 종려나무 아래",
        "ANCHOR_JDG_4_5",
        "드보라 종려 은유는 분산 판단 센터·중재 노드 비유이며, 식물이 아님.",
        [
            n("사사기 4:6", "너는 납달리 지파 중", "is_called_barak_of", "called Barak — delegate lead", "research_metaphor_delegate_lead"),
            n("사사기 4:9", "네가 가는 길에 내가 함께", "is_go_with_you_of", "go with you — pair programming", "research_metaphor_pair_programming"),
            n("사사기 5:7", "이스라엘의 촌락이", "is_villages_ceased_of", "villages ceased — quiet period", "research_metaphor_quiet_period"),
            n("잠언 31:26", "지혜의 법을 말하며", "is_opened_mouth_wisdom_of", "opened mouth wisdom — runbook voice", "research_metaphor_runbook_voice"),
        ],
    ),
    row(
        "peter_vision_sheet",
        "베드로 보자기 (Peter Vision Sheet)",
        "사도행전 10:11",
        "큰 보자기 같은 그릇을",
        "ANCHOR_ACT_10_11",
        "보자기 은유는 정책 예외·다중 테넌트 허용 비유이며, 환각이 아님.",
        [
            n("사도행전 10:15", "하나님이 정하신 것을", "is_what_god_cleansed_of", "what God cleansed — allowlist expand", "research_metaphor_allowlist_expand"),
            n("사도행전 10:28", "율법으로는 더럽다고", "is_unlawful_associate_of", "unlawful associate — old deny rule", "research_metaphor_old_deny_rule"),
            n("갈라디아서 2:12", "두려워한 까닭에", "is_withdrew_fear_of", "withdrew fear — policy regression", "research_metaphor_policy_regression"),
            n("로마서 14:14", "주 예수로 말미암아", "is_nothing_unclean_of", "nothing unclean — neutral artifact", "research_metaphor_neutral_artifact"),
        ],
    ),
    row(
        "acts_church_share",
        "초대 교회 나눔 (Acts Church Share)",
        "사도행전 2:44",
        "믿는 사람이 다 한 마음",
        "ANCHOR_ACT_2_44",
        "나눔 은유는 공유 인프라·비용 풀링 비유이며, 공산주의 단정 아님.",
        [
            n("사도행전 4:32", "물건을 자기 것이라 하는 자가", "is_one_heart_of", "one heart — shared state", "research_metaphor_shared_state"),
            n("사도행전 4:35", "각 사람의 필요를 따라", "is_distributed_need_of", "distributed need — fair queue", "research_metaphor_fair_queue"),
            n("고린도후서 8:14", "너희의 풍부함이", "is_equality_supply_of", "equality supply — load balance", "research_metaphor_load_balance"),
            n("히브리서 10:25", "모이기를 폐하지 말라", "is_not_forsaking_of", "not forsaking — standup ritual", "research_metaphor_standup_ritual"),
        ],
    ),
    row(
        "timothy_scroll",
        "디모데 두루마리 (Timothy Scroll)",
        "디모데후서 3:15",
        "어려서부터 성경을 알았나니",
        "ANCHOR_2TI_3_15",
        "두루마리 은유는 온보딩 문서·레거시 지식 비유이며, 고고학이 아님.",
        [
            n("디모데후서 1:5", "로이의 안에서 있는 믿음을", "is_sincere_faith_of", "sincere faith — mentor lineage", "research_metaphor_mentor_lineage"),
            n("디모데전서 4:12", "네가 젊음을 인하여", "is_young_example_of", "young example — junior lead", "research_metaphor_junior_lead"),
            n("딤전 4:13", "독서와 권면과 가르침에", "is_reading_exhortation_of", "reading exhortation — doc review", "research_metaphor_doc_review"),
            n("시편 119:11", "내가 주의 말씀을 내 마음에", "is_word_heart_of", "word heart — internal wiki", "research_metaphor_internal_wiki"),
        ],
    ),
    row(
        "titus_island",
        "디도 섬 (Titus Island)",
        "디도서 1:5",
        "내가 너를 그 섬에 남겨 둔 것은",
        "ANCHOR_TIT_1_5",
        "디도 섬 은유는 원격 사이트·단독 운영 책임 비유이며, 지리가 아님.",
        [
            n("디도서 1:7", "감독은 하나님의 청지기로", "is_overseer_steward_of", "overseer steward — site lead", "research_metaphor_site_lead"),
            n("디도서 2:7", "모든 일에 네 자신을", "is_pattern_good_of", "pattern good — golden image", "research_metaphor_golden_image"),
            n("디도서 3:9", "어리석은 변론과", "is_foolish_disputes_of", "foolish disputes — bike shed", "research_metaphor_bike_shed"),
            n("고린도후서 8:23", "내 동역자요 너희의 사도요", "is_partner_apostle_of", "partner apostle — field engineer", "research_metaphor_field_engineer"),
        ],
    ),
    row(
        "healing_pool",
        "베데스다 못 (Healing Pool)",
        "요한복음 5:2",
        "예루살렘에 양문 곁에",
        "ANCHOR_JHN_5_2",
        "베데스다 못 은유는 배치 치유 큐·스테일 워커 비유이며, 의료가 아님.",
        [
            n("요한복음 5:7", "물이 동할 때에", "is_troubled_water_of", "troubled water — job window", "research_metaphor_job_window"),
            n("요한복음 5:9", "그 병이 나은지라", "is_made_well_of", "made well — ticket cleared", "research_metaphor_ticket_cleared"),
            n("요한복음 5:14", "다시는 죄를 범하지 말라", "is_sin_no_more_of", "sin no more — prevent relapse", "research_metaphor_prevent_relapse"),
            n("잠언 14:30", "마음의 화목은 육체의 생명이라", "is_sound_heart_of", "sound heart — healthy node", "research_metaphor_healthy_node"),
        ],
    ),
    row(
        "pool_bethesda",
        "베데스다 다섯 포르치 (Pool Bethesda)",
        "요한복음 5:3",
        "병든 자, 맹인과",
        "ANCHOR_JHN_5_3",
        "다섯 포르치 은유는 다중 대기열·우선순위 경쟁 비유이며, 건축이 아님.",
        [
            n("요한복음 5:5", "삼십팔 해 된 병자가", "is_thirty_eight_years_of", "thirty eight years — stale ticket", "research_metaphor_stale_ticket"),
            n("요한복음 5:7", "나를 못에 넣어 줄 사람이", "is_no_man_of", "no man — no owner", "research_metaphor_no_owner"),
            n("요한복음 5:8", "일어나 네 자리를 가지라", "is_rise_walk_of", "rise walk — unstick queue", "research_metaphor_unstick_queue"),
            n("레위기 15:31", "더럽게 하여 내 성막을", "is_defile_tabernacle_of", "defile tabernacle — contaminate cluster", "research_metaphor_contaminate_cluster"),
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
