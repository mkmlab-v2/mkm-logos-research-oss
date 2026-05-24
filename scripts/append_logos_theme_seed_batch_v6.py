#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v6, Track B NON_GATING)."""
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
        "solomon_temple_dedic",
        "솔로몬 성전 봉헌 (Solomon Temple Dedication)",
        "열왕기상 8:10",
        "제사장들이 성소에서 나오지 못하니",
        "ANCHOR_1KI_8_10",
        "성전 봉헌 은유는 프로덕션 런칭·대규모 점검 비유이며, 부동산이 아님.",
        [
            n("열왕기상 8:27", "하늘과 하늘의 하늘이라도", "is_heaven_cannot_of", "heaven cannot — scale limits", "research_metaphor_scale_limits"),
            n("열왕기상 8:61", "마음을 여호와께 향하여", "is_perfect_heart_of", "perfect heart — aligned SLO", "research_metaphor_aligned_slo"),
            n("역대하 7:1", "솔로몬이 기도하기를 마치매", "is_fire_consumed_of", "fire consumed — load test pass", "research_metaphor_load_test_pass"),
            n("요한복음 2:19", "이 성전을 허시고", "is_destroy_temple_of", "destroy temple — rebuild v2", "research_metaphor_rebuild_v2"),
        ],
    ),
    row(
        "elijah_fire_heaven",
        "엘리야 불 (Elijah Fire from Heaven)",
        "열왕기상 18:38",
        "불이 내려서",
        "ANCHOR_1KI_18_38B",
        "하늘 불 은유는 결정적 벤치 승리·자동 롤백 비유이며, 실화가 아님.",
        [
            n("열왕기상 18:24", "이 신을 부르는 자에게", "is_call_answer_of", "call answer — benchmark responds", "research_metaphor_benchmark_responds"),
            n("열왕기상 18:39", "여호와 그는 하나님이시로다", "is_lord_is_god_of", "Lord is God — clear winner", "research_metaphor_clear_winner"),
            n("누가복음 9:54", "불을 명하여 내려", "is_fire_command_of", "fire command — destructive ops", "research_metaphor_destructive_ops"),
            n("히브리서 12:29", "우리 하나님은 소멸하는 불이시라", "is_consuming_fire_of", "consuming fire — burn bad deploy", "research_metaphor_burn_bad_deploy"),
        ],
    ),
    row(
        "naomi_return",
        "나오미 귀환 (Naomi Return)",
        "룻기 1:16",
        "당신이 가시는 곳에 나도 가며",
        "ANCHOR_RUT_1_16",
        "나오미 은유는 레거시 마이그레이션·팀 귀환 비유이며, 이민이 아님.",
        [
            n("룻기 1:20", "나를 나오미라 부르지 말고", "is_call_mara_of", "call Mara — rename after incident", "research_metaphor_rename_after_incident"),
            n("룻기 1:22", "나오미가 모압 땅에서", "is_returned_bethlehem_of", "returned Bethlehem — cutover home", "research_metaphor_cutover_home"),
            n("룻기 4:14", "여호와께서 생명의 구원자를", "is_redeemer_given_of", "redeemer given — sponsor found", "research_metaphor_sponsor_found"),
            n("이사야 35:10", "구속함을 받은 자들이", "is_ransomed_return_of", "ransomed return — DR success", "research_metaphor_dr_success"),
        ],
    ),
    row(
        "esther_fast",
        "에스더 금식 (Esther Fast)",
        "에스더 4:16",
        "내가 금식하고 밤낮으로",
        "ANCHOR_EST_4_16",
        "금식 은유는 변경 동결·집중 복구 창 비유이며, 다이어트가 아님.",
        [
            n("에스더 4:14", "이 때를 위하여", "is_for_such_time_of", "for such time — duty window", "research_metaphor_duty_window"),
            n("에스더 5:1", "왕의 복을 입고", "is_royal_robes_of", "royal robes — prod credentials", "research_metaphor_prod_credentials"),
            n("에스더 9:22", "기쁨과 잔치의 날", "is_joy_feast_of", "joy feast — celebrate fix", "research_metaphor_celebrate_fix"),
            n("이사야 58:6", "금식하는 날이 어찌", "is_true_fast_of", "true fast — real maintenance", "research_metaphor_real_maintenance"),
        ],
    ),
    row(
        "mordecai_gate",
        "모르드개 문 (Mordecai Gate)",
        "에스더 2:21",
        "왕의 문을 지키던 두 환관",
        "ANCHOR_EST_2_21",
        "모르드개 문 은유는 내부자 제보·보안 인텔 비유이며, 출입통제가 아님.",
        [
            n("에스더 2:22", "모르드개가 알고 왕후 에스더에게", "is_told_esther_of", "told Esther — escalate intel", "research_metaphor_escalate_intel"),
            n("에스더 6:2", "모르드개가 왕을 위하여", "is_mordecai_recorded_of", "recorded good — audit log credit", "research_metaphor_audit_log_credit"),
            n("에스더 8:2", "왕의 인을 주매", "is_signet_given_of", "signet given — signing key", "research_metaphor_signing_key"),
            n("잠언 11:14", "지략이 없으면 백성이 엎드러지나", "is_no_counsel_falls_of", "no counsel falls — need advisors", "research_metaphor_need_advisors"),
        ],
    ),
    row(
        "nehemiah_cupbearer",
        "느헤미야 술관원 (Nehemiah Cupbearer)",
        "느헤미야 2:1",
        "아닥사스타 왕 제이십년",
        "ANCHOR_NEH_2_1",
        "술관원 은유는 신뢰된 SRE·근접 권한 비유이며, 주류가 아님.",
        [
            n("느헤미야 1:4", "앉아서 울며 슬퍼하며", "is_wept_mourned_of", "wept mourned — status page red", "research_metaphor_status_page_red"),
            n("느헤미야 2:5", "왕이 내게 이르시되", "is_king_asked_of", "king asked — exec approval", "research_metaphor_exec_approval"),
            n("느헤미야 4:9", "우리 하나님이 우리를 기억하사", "is_god_fought_of", "God fought — platform shield", "research_metaphor_platform_shield"),
            n("로마서 12:15", "함께 기뻐하고", "is_rejoice_weep_of", "rejoice weep — empathetic on-call", "research_metaphor_empathetic_oncall"),
        ],
    ),
    row(
        "ezra_fast",
        "에스라 금식 (Ezra Fast)",
        "에스라 8:21",
        "거기서 금식하여 우리 하나님 앞에서",
        "ANCHOR_EZR_8_21",
        "에스라 금식 은유는 배포 전 검증·리스크 감소 비유이며, 종교가 아님.",
        [
            n("에스라 7:10", "율법을 연구하여 실행하며", "is_studied_law_of", "studied law — read SSOT", "research_metaphor_read_ssot"),
            n("에스라 8:23", "우리를 길에서 보호하실지라", "is_fast_safe_of", "fast safe — preflight checks", "research_metaphor_preflight_checks"),
            n("에스라 9:4", "무리가 크게 떨며", "is_trembled_greatly_of", "trembled — audit shock", "research_metaphor_audit_shock"),
            n("느헤미야 8:18", "첫날부터 마지막 날까지", "is_read_aloud_of", "read aloud — team walkthrough", "research_metaphor_team_walkthrough"),
        ],
    ),
    row(
        "job_friends",
        "욥 친구 (Job Friends)",
        "욥기 2:11",
        "그의 친구 세 사람이",
        "ANCHOR_JOB_2_11",
        "욥 친구 은유는 잘못된 RCA·블레임 게임 비유이며, 상담이 아님.",
        [
            n("욥기 2:13", "칠 일과 칠 야를 동하여", "is_sat_seven_of", "sat seven — long war room", "research_metaphor_long_war_room"),
            n("욥기 42:7", "너희가 내 종 욥에게 대하여", "is_spoke_not_right_of", "spoke not right — bad postmortem", "research_metaphor_bad_postmortem"),
            n("잠언 17:17", "어려울 때에 형제를 사랑하는", "is_loves_at_all_of", "loves at all — real ally", "research_metaphor_real_ally"),
            n("갈라디아서 6:2", "서로의 짐을 지라", "is_bear_burdens_of", "bear burdens — pair on-call", "research_metaphor_pair_oncall"),
        ],
    ),
    row(
        "isaiah_coal",
        "이사야 숯 (Isaiah Coal)",
        "이사야 6:6",
        "화저로 단 숯을 내 입에 대며",
        "ANCHOR_ISA_6_6",
        "숯 은유는 접근 권한 정화·감사 통과 비유이며, 화상이 아님.",
        [
            n("이사야 6:5", "화로자여 나는 망하였다", "is_woe_unclean_of", "woe unclean — failed audit", "research_metaphor_failed_audit"),
            n("이사야 6:8", "내가 여기 있나이다 나를 보내소서", "is_here_send_me_of", "here send me — volunteer deploy", "research_metaphor_volunteer_deploy"),
            n("예레미야 1:9", "보라 내가 네 입에 말을 두었노라", "is_put_words_of", "put words — inject config", "research_metaphor_inject_config"),
            n("시편 51:7", "죄를 씻어 나를 정결하게", "is_purge_hyssop_of", "purge hyssop — scrub logs", "research_metaphor_scrub_logs"),
        ],
    ),
    row(
        "jeremiah_cistern",
        "예레미야 웅덩이 (Jeremiah Cistern)",
        "예레미야 38:6",
        "웅덩이에 가두었으니",
        "ANCHOR_JER_38_6",
        "웅덩이 은유는 격리 샌드박스·에스컬레이션 실패 비유이며, 구속이 아님.",
        [
            n("예레미야 38:10", "왕이 에덴 왕궁에서", "is_took_thirty_of", "took thirty — rescue team", "research_metaphor_rescue_team"),
            n("예레미야 38:13", "웅덩이에는 물이 없고", "is_no_water_mud_of", "no water mud — stuck state", "research_metaphor_stuck_state"),
            n("시편 40:2", "진흙 웅덩이와 수렁에서", "is_pit_miry_of", "pit miry — debt swamp", "research_metaphor_debt_swamp"),
            n("창세기 37:24", "빈 웅덩이에 넣으매", "is_empty_pit_of", "empty pit — quarantine", "research_metaphor_quarantine"),
        ],
    ),
    row(
        "amos_basket_fruit",
        "아모스 과일 바구니 (Amos Basket Fruit)",
        "아모스 8:2",
        "여름 과일이 익은 바구니가",
        "ANCHOR_AMO_8_2",
        "바구니 은유는 만기 SLA·서비스 EOL 비유이며, 농산물가 아님.",
        [
            n("아모스 8:11", "기근이 이 땅에 임할 것이라", "is_famine_word_of", "famine word — doc drought", "research_metaphor_doc_drought"),
            n("아모스 9:13", "추수할 자가 추수하는 것보다", "is_plowman_overtake_of", "plowman overtake — fast recovery", "research_metaphor_fast_recovery"),
            n("레위기 23:39", "열매를 거둔 후에", "is_feast_ingathering_of", "feast ingathering — release harvest", "research_metaphor_release_harvest"),
            n("마태복음 9:37", "추수할 것은 많으나", "is_harvest_plenteous_of", "harvest plenteous — backlog", "research_metaphor_backlog"),
        ],
    ),
    row(
        "micah_bethlehem",
        "미가 베들레헴 (Micah Bethlehem)",
        "미가 5:2",
        "베들레헴 에브라다야 너는",
        "ANCHOR_MIC_5_2",
        "베들레헴 은유는 소규모 출발·엣지 릴리스 비유이며, 지정학이 아님.",
        [
            n("미가 6:8", "정의를 행하며 인애를 베풀며", "is_do_justly_of", "do justly — fairness", "research_metaphor_fairness"),
            n("룻기 1:2", "유다 베들레헴에 가서", "is_bethlehem_judah_of", "Bethlehem Judah — small origin", "research_metaphor_small_origin"),
            n("마태복음 2:6", "유다 땅 베들레헴아", "is_matthew_bethlehem_of", "Matthew Bethlehem — prophecy deploy", "research_metaphor_prophecy_deploy"),
            n("요한복음 7:42", "그리스도가 다윗의 씨에서", "is_seed_david_of", "seed David — lineage trace", "research_metaphor_lineage_trace"),
        ],
    ),
    row(
        "nahum_lion",
        "나훔 사자 (Nahum Lion)",
        "나훔 2:11",
        "사자의 굴이 어디냐",
        "ANCHOR_NAH_2_11",
        "사자 은유는 위협 액터 소멸·침입자 제거 비유이며, 동물이 아님.",
        [
            n("나훔 1:7", "여호와는 선한 자의 피난처시요", "is_refuge_trouble_of", "refuge trouble — safe region", "research_metaphor_safe_region"),
            n("나훔 2:13", "네 모든 군대를 멸하리라", "is_cut_off_of", "cut off — revoke keys", "research_metaphor_revoke_keys"),
            n("베드로전서 5:8", "우는 사자 같이", "is_roaring_lion_of", "roaring lion — threat actor", "research_metaphor_threat_actor"),
            n("아모스 3:8", "사자가 부르짖으면", "is_lion_roars_of", "lion roars — alert fired", "research_metaphor_alert_fired"),
        ],
    ),
    row(
        "habakkuk_faith",
        "하박국 믿음 (Habakkuk Faith)",
        "하박국 2:4",
        "오직 의인은 그의 믿음으로 말미암아",
        "ANCHOR_HAB_2_4",
        "믿음 은유는 게이트 통과 신뢰·롤아웃 신뢰 비유이며, 종교가 아님.",
        [
            n("하박국 1:5", "너희는 열방 중에서", "is_among_nations_of", "among nations — global scope", "research_metaphor_global_scope"),
            n("하박국 3:17", "무화과나무가 열매를 맺지 못하며", "is_no_fig_flock_of", "no fig flock — total outage", "research_metaphor_total_outage"),
            n("하박국 3:18", "나는 여호와로 말미암아", "is_will_rejoice_of", "will rejoice — still ship", "research_metaphor_still_ship"),
            n("로마서 1:17", "믿음으로 말미암아 의에 이르게", "is_faith_to_faith_of", "faith to faith — progressive deploy", "research_metaphor_progressive_deploy"),
        ],
    ),
    row(
        "zephaniah_sing",
        "스바냐 노래 (Zephaniah Sing)",
        "스바냐 3:14",
        "딸 시온아 노래하라",
        "ANCHOR_ZEP_3_14",
        "노래 은유는 장애 종료·그린 회고 비유이며, 엔터테인이 아님.",
        [
            n("스바냐 3:17", "그가 너를 기뻐하시며", "is_rejoices_over_of", "rejoices over — green retro", "research_metaphor_green_retro"),
            n("스바냐 3:19", "내가 그 때에 너희를 구원하여", "is_save_time_of", "save time — incident resolved", "research_metaphor_incident_resolved"),
            n("이사야 12:1", "여호와께서 나를 노하게 하셨다가", "is_anger_turned_of", "anger turned — status green", "research_metaphor_status_green"),
            n("시편 98:1", "새 노래를 불러", "is_new_song_of", "new song — release notes joy", "research_metaphor_release_notes_joy"),
        ],
    ),
    row(
        "james_tongue",
        "야고보 혀 (James Tongue)",
        "야고보서 3:6",
        "혀는 불의 세계라",
        "ANCHOR_JAS_3_6",
        "혀 은유는 채팅·로그 오남용·커뮤니케이션 리스크 비유이며, 신체가 아님.",
        [
            n("야고보서 3:8", "혀를 길들이기가 누구든지 할 수 없느니라", "is_no_man_tame_of", "no man tame — unbounded chat", "research_metaphor_unbounded_chat"),
            n("야고보서 1:19", "듣기는 속히 하고 말하기는 더디 하며", "is_swift_hear_of", "swift hear — listen first", "research_metaphor_listen_first"),
            n("잠언 18:21", "죽고 사는 권세가 혀에 있나니", "is_death_life_of", "death life — words matter", "research_metaphor_words_matter"),
            n("에베소서 4:29", "덕을 세우는 말만", "is_edifying_speech_of", "edifying speech — constructive comms", "research_metaphor_constructive_comms"),
        ],
    ),
    row(
        "jude_contend",
        "유다 투쟁 (Jude Contend)",
        "유다서 1:3",
        "성도들에게 한 번 주신 믿음을",
        "ANCHOR_JUD_1_3",
        "유다 투쟁 은유는 스키마·계약 방어·보안 패치 비유이며, 소송이 아님.",
        [
            n("유다서 1:4", "거짓 형제들이 가만히 들어왔으니", "is_ungodly_turned_of", "ungodly turned — supply chain risk", "research_metaphor_supply_chain_risk"),
            n("유다서 1:20", "거룩한 믿음 위에", "is_build_yourselves_of", "build yourselves — harden baseline", "research_metaphor_harden_baseline"),
            n("유다서 1:24", "너희를 보존하사", "is_able_keep_of", "able keep — platform guard", "research_metaphor_platform_guard"),
            n("갈라디아서 5:1", "그리스도께서 우리를 자유롭게", "is_liberty_christ_of", "liberty Christ — no vendor lock", "research_metaphor_no_vendor_lock"),
        ],
    ),
    row(
        "revelation_lamb",
        "계시록 어린양 (Revelation Lamb)",
        "요한계시록 5:6",
        "어린 양이 있는데",
        "ANCHOR_REV_5_6",
        "어린양 은유는 무결성·감사 통과 희생 비유이며, 가격이 아님.",
        [
            n("요한계시록 5:9", "보아 온 땅에서 사람들을", "is_purchased_blood_of", "purchased blood — paid cost", "research_metaphor_paid_cost"),
            n("요한계시록 7:17", "보좌 가운데 어린 양이", "is_lamb_throne_of", "lamb throne — central service", "research_metaphor_central_service"),
            n("요한복음 1:29", "세상 죄를 지고 가는", "is_lamb_god_of", "lamb God — absorbs blast", "research_metaphor_absorbs_blast"),
            n("이사야 53:7", "그가 괴로울 때에도 열어서", "is_silent_lamb_of", "silent lamb — no blame shift", "research_metaphor_no_blame_shift"),
        ],
    ),
    row(
        "whale_jonah",
        "요나 큰 물고기 (Whale Jonah)",
        "요나 1:17",
        "여호와께서 큰 물고기를 예비하사",
        "ANCHOR_JON_1_17B",
        "요나 고래 은유는 격리·롤백 버퍼 비유이며, 생물이 아님.",
        [
            n("요나 2:1", "물고기 뱃속에서", "is_belly_prayed_of", "belly prayed — bridge incident", "research_metaphor_bridge_incident"),
            n("요나 2:10", "물고기에게 말씀하시매", "is_vomited_dry_of", "vomited dry — released hold", "research_metaphor_released_hold"),
            n("마태복음 12:40", "요나가 삼일 밤낮을", "is_three_days_of", "three days — max window", "research_metaphor_max_window"),
            n("요나 3:3", "니느웨로 가라", "is_go_nineveh_of", "go Nineveh — duty after fix", "research_metaphor_duty_after_fix"),
        ],
    ),
    row(
        "goliath_stone",
        "골리앗 돌 (Goliath Stone)",
        "사무엘상 17:49",
        "다윗이 손을 주머니에서",
        "ANCHOR_1SA_17_49",
        "돌 은유는 소형 패치·언더도그 승리 비유이며, 무기가 아님.",
        [
            n("사무엘상 17:45", "너는 칼과 창과 단창으로", "is_sword_spear_of", "sword spear — heavy stack", "research_metaphor_heavy_stack"),
            n("사무엘상 17:50", "다윗이 골리앗을 죽이고", "is_slew_goliath_of", "slew Goliath — underdog win", "research_metaphor_underdog_win"),
            n("시편 144:1", "내 손을 싸우게 하시며", "is_trains_hands_of", "trains hands — skill up", "research_metaphor_skill_up"),
            n("잠언 21:31", "말은 전일을 위하여 예비하되", "is_horse_day_of", "horse day — not enough alone", "research_metaphor_not_enough_alone"),
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
