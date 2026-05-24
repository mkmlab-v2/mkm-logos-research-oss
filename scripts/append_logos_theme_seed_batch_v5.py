#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v5, Track B NON_GATING)."""
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
        "saul_spirit_departed",
        "사울 영 떠남 (Saul Spirit Departed)",
        "사무엘상 16:14",
        "여호와의 영이 사울에게서 떠나시고",
        "ANCHOR_1SA_16_14",
        "사울 은유는 SLO 붕괴·온콜 커버리지 상실 비유이며, 정신건강 단정이 아님.",
        [
            n("사무엘상 18:12", "사울이 다윗을 두려워하니", "is_afraid_david_of", "afraid David — rival service", "research_metaphor_rival_service"),
            n("사무엘상 28:7", "밤에 일어나 옷을 입고", "is_consulted_medium_of", "consulted medium — shadow on-call", "research_metaphor_shadow_oncall"),
            n("시편 51:11", "주의 성신을 내게서 거두지 마시며", "is_do_not_take_of", "do not take — keep pager", "research_metaphor_keep_pager"),
            n("갈라디아서 5:22", "성령의 열매는", "is_fruit_spirit_of", "fruit spirit — healthy metrics", "research_metaphor_healthy_metrics"),
        ],
    ),
    row(
        "absalom_hair",
        "압살롬 머리카락 (Absalom Hair)",
        "사무엘하 18:9",
        "그 머리가 그 위에 있는 참나무 가지에",
        "ANCHOR_2SA_18_9",
        "압살론 은유는 단일 장애점·과도한 자신 비유이며, 외모가 아님.",
        [
            n("사무엘하 14:26", "머리털을 밀 때에 저울에 달면", "is_heavy_hair_of", "heavy hair — vanity metric", "research_metaphor_vanity_metric"),
            n("사무엘하 15:6", "이스라엘 가운데서 자기에게로", "is_stole_hearts_of", "stole hearts — shadow IT", "research_metaphor_shadow_it"),
            n("사무엘하 18:14", "내가 만일 그를 살려두면", "is_would_leave_of", "would leave — cut losses", "research_metaphor_cut_losses"),
            n("잠언 16:18", "교만은 패망의 선봉이요", "is_pride_before_fall_of", "pride before fall — hubris", "research_metaphor_hubris"),
        ],
    ),
    row(
        "athaniah_crown",
        "아탈야 왕위 (Athaliah Usurpation)",
        "열왕기하 11:12",
        "그에게 면류관을 씌우고 기름을 부어",
        "ANCHOR_2KI_11_12",
        "아탈야 은유는 비인가 승격·권한 탈취 비유이며, 정치 예측이 아님.",
        [
            n("열왕기하 11:1", "아하시야의 어머니 아탈야가", "is_destroyed_seed_of", "destroyed seed — kill canary", "research_metaphor_kill_canary"),
            n("열왕기하 11:2", "요아스 왕의 아들 요아스를", "is_hid_child_of", "hid child — secret backup", "research_metaphor_secret_backup"),
            n("열왕기하 11:12", "왕이 되었더라", "is_made_king_of", "made king — restored legit", "research_metaphor_restored_legit"),
            n("시편 2:2", "여호와와 그의 기름부음을 받은 자를", "is_rage_nations_of", "rage nations — hostile takeover", "research_metaphor_hostile_takeover"),
        ],
    ),
    row(
        "jehoiada_crown",
        "여호야다 왕관 (Jehoiada Crown)",
        "열왕기하 11:12",
        "그에게 면류관을 씌우고",
        "ANCHOR_2KI_11_12B",
        "여호야다 은유는 감사 복구·숨은 계정 복원 비유이며, 왕정이 아님.",
        [
            n("열왕기하 11:4", "여호야다가 백성과 말하고", "is_jehoiada_covenanted_of", "covenanted — change advisory", "research_metaphor_change_advisory"),
            n("열왕기하 11:17", "여호와께서 다윗의 종에게", "is_made_covenant_of", "made covenant — policy reset", "research_metaphor_policy_reset"),
            n("역대하 24:2", "여호야다가 살아 있는 날 동안", "is_did_right_of", "did right — mentor era", "research_metaphor_mentor_era"),
            n("히브리서 12:1", "구름같이 둘러싼 증인들을", "is_witnesses_cloud_of", "witness cloud — audit trail", "research_metaphor_audit_trail"),
        ],
    ),
    row(
        "hezekiah_plague",
        "히스기야 역병 (Hezekiah Plague)",
        "역대하 32:21",
        "여호와의 사자가 나가서",
        "ANCHOR_2CH_32_21",
        "역병 은유는 대규모 장애 자동 완화·패치 비유이며, 질병 예측이 아님.",
        [
            n("역대하 32:1", "산헤립이 와서", "is_sennacherib_came_of", "Sennacherib came — DDoS wave", "research_metaphor_ddos_wave"),
            n("이사야 37:36", "여호와의 사자가 나가서", "is_angel_struck_of", "angel struck — auto remediate", "research_metaphor_auto_remediate"),
            n("역대하 32:24", "그 병이 죽게 되매", "is_sick_to_death_of", "sick to death — P0 health", "research_metaphor_p0_health"),
            n("시편 91:6", "밤에 창궐하는 염병을", "is_pestilence_dark_of", "pestilence dark — night incident", "research_metaphor_night_incident"),
        ],
    ),
    row(
        "manasseh_repent",
        "므낫세 회개 (Manasseh Repentance)",
        "역대하 33:13",
        "그가 여호와께 기도하고",
        "ANCHOR_2CH_33_13",
        "므낫세 은유는 레거시 테넌트 복구·사후 감사 비유이며, 도덕 판결이 아님.",
        [
            n("역대하 33:9", "므낫세가 유도하여", "is_did_evil_of", "did evil — tech debt era", "research_metaphor_tech_debt_era"),
            n("역대하 33:11", "바벨론 왕의 관원들이", "is_taken_babylon_of", "taken Babylon — account suspended", "research_metaphor_account_suspended"),
            n("역대하 33:16", "여호와의 제단을 수축하고", "is_rebuilt_altar_of", "rebuilt altar — restore core", "research_metaphor_restore_core"),
            n("예레미야 15:1", "모세와 사무엘도", "is_moses_samuel_of", "Moses Samuel — appeal history", "research_metaphor_appeal_history"),
        ],
    ),
    row(
        "josiah_passover",
        "요시야 유월절 (Josiah Passover)",
        "역대하 35:18",
        "이스라엘에서 요시야 왕 때와 같이",
        "ANCHOR_2CH_35_18",
        "유월절 은유는 대규모 릴리스 점검·레거시 정리 비유이며, 명절이 아님.",
        [
            n("역대하 34:8", "그의 통치 제십팔년에", "is_eighteenth_year_of", "eighteenth year — mature audit", "research_metaphor_mature_audit"),
            n("역대하 35:1", "여호와께 유월절을 지켰으니", "is_kept_passover_of", "kept Passover — major deploy", "research_metaphor_major_deploy"),
            n("열왕기하 23:25", "나와 같은 마음을 가진 왕이", "is_like_him_of", "like him — gold standard", "research_metaphor_gold_standard"),
            n("고린도전서 5:7", "우리의 유월절 양", "is_christ_passover_of", "Christ Passover — canonical", "research_metaphor_canonical"),
        ],
    ),
    row(
        "daniel_writing_wall",
        "벨사살 손가락 글 (Writing on Wall)",
        "다니엘 5:25",
        "메네 메네 데겔 우바르신",
        "ANCHOR_DAN_5_25B",
        "벽 글 은유는 감사 경고·SLO 위반 통지 비유이며, 주가 예측이 아님.",
        [
            n("다니엘 5:5", "사람의 손가락이 나타나", "is_hand_appeared_of", "hand appeared — unexplained alert", "research_metaphor_unexplained_alert"),
            n("다니엘 5:26", "메네는 하나님이 왕의 나라를", "is_mene_numbered_of", "Mene numbered — quota exceeded", "research_metaphor_quota_exceeded"),
            n("다니엘 5:30", "그 밤에 갈대아 사람", "is_same_night_of", "same night — no grace", "research_metaphor_no_grace"),
            n("요한복음 8:7", "죄 없는 자가 먼저", "is_without_sin_of", "without sin — blame gate", "research_metaphor_blame_gate"),
        ],
    ),
    row(
        "habakkuk_watchtower",
        "하박국 망대 (Habakkuk Watchtower)",
        "하박국 2:1",
        "내가 내 파수대에 서서",
        "ANCHOR_HAB_2_1B",
        "망대 은유는 관측·대기 응답 비유이며, 타이밍 매매가 아님.",
        [
            n("하박국 2:2", "여호와께서 내게 대답하시며", "is_write_vision_of", "write vision — ticket from watch", "research_metaphor_ticket_from_watch"),
            n("하박국 2:3", "정한 때가 있으니", "is_appointed_time_of", "appointed time — scheduled fix", "research_metaphor_scheduled_fix"),
            n("이사야 21:11", "파수꾼아 밤이 얼마나", "is_watchman_night_of", "watchman night — on-call ask", "research_metaphor_oncall_ask"),
            n("시편 130:5", "여호와를 기다리며", "is_wait_lord_of", "wait Lord — queue backlog", "research_metaphor_queue_backlog"),
        ],
    ),
    row(
        "obadiah_edom",
        "오바댜 에돔 (Obadiah Edom)",
        "오바댜 1:15",
        "여호와의 날이 만국에 임할 것이니",
        "ANCHOR_OBA_1_15",
        "에돔 은유는 형제 테넌트 배신·경쟁 리전 비유이며, 지정학이 아님.",
        [
            n("오바댜 1:10", "형제 야곱을 대적하여", "is_violence_brother_of", "violence brother — cross-tenant harm", "research_metaphor_cross_tenant_harm"),
            n("오바댜 1:12", "형제의 날 곧 그 재앙의 날에", "is_rejoiced_distress_of", "rejoiced distress — toxic neighbor", "research_metaphor_toxic_neighbor"),
            n("아모스 1:11", "에돔이 칼을 들어", "is_pursued_sword_of", "pursued sword — aggressive peer", "research_metaphor_aggressive_peer"),
            n("말라기 1:2", "야곱을 사랑하였고", "is_loved_jacob_of", "loved Jacob — primary tenant", "research_metaphor_primary_tenant"),
        ],
    ),
    row(
        "haggai_zerubbabel",
        "학개 스룹바벨 (Haggai Zerubbabel)",
        "학개 2:23",
        "내가 너를 택하였나니",
        "ANCHOR_HAG_2_23",
        "스룹바벨 은유는 재건 PM·릴리스 오너 비유이며, 정치가 아님.",
        [
            n("학개 1:14", "스룹바벨과 여호수아와", "is_stirred_spirit_of", "stirred spirit — reboot team", "research_metaphor_reboot_team"),
            n("학개 2:4", "스룹바벨아 강하고 담대하라", "is_be_strong_of", "be strong — incident lead", "research_metaphor_incident_lead"),
            n("스가랴 4:10", "작은 일을 멸시하지 말라", "is_despise_small_of", "despise not small — incremental", "research_metaphor_incremental"),
            n("에스겔 37:24", "내 종 다윗이 그들의 왕이 되리라", "is_david_king_of", "David king — target state", "research_metaphor_target_state"),
        ],
    ),
    row(
        "zechariah_lampstand",
        "스가랴 촛대 (Zechariah Lampstand)",
        "스가랴 4:2",
        "촛대 하나가 있고 그 위에",
        "ANCHOR_ZEC_4_2",
        "촛대 은유는 HA 클러스터·다중 노드 가용 비유이며, 조명이 아님.",
        [
            n("스가랴 4:6", "말과 그 마는 자로 말미암지 아니하고", "is_not_by_might_of", "not by might — orchestrator", "research_metaphor_orchestrator"),
            n("출애굽기 25:37", "일곱 등잔을 만들지니라", "is_seven_lamps_of", "seven lamps — seven replicas", "research_metaphor_seven_replicas"),
            n("요한계시록 1:12", "일곱 금 촛대 사이에", "is_seven_lampstands_of", "seven lampstands — multi region", "research_metaphor_multi_region"),
            n("마태복음 5:15", "등불을 말 아래 두지 아니하고", "is_light_bushel_of", "not under bushel — expose metrics", "research_metaphor_expose_metrics"),
        ],
    ),
    row(
        "malachi_sun",
        "말라기 해 (Malachi Sun)",
        "말라기 4:2",
        "공의로운 해가 떠올라서",
        "ANCHOR_MAL_4_2",
        "해 은유는 회복·투명성 SLA 비유이며, 기후가 아님.",
        [
            n("말라기 3:1", "내가 내 사자를 보내리니", "is_messenger_sent_of", "messenger sent — deploy bot", "research_metaphor_deploy_bot"),
            n("말라기 3:10", "창고에 십일조를", "is_storehouse_tithe_of", "storehouse — budget reserve", "research_metaphor_budget_reserve"),
            n("누가복음 1:78", "높으신 이의 긍휼로", "is_dayspring_of", "dayspring — dawn after outage", "research_metaphor_dawn_after_outage"),
            n("시편 84:11", "여호와 하나님은 해요", "is_sun_shield_of", "sun shield — protect and light", "research_metaphor_protect_and_light"),
        ],
    ),
    row(
        "balaam_oracle",
        "발람 신탁 (Balaam Oracle)",
        "민수기 24:17",
        "한 별이 야곱에게서 나오며",
        "ANCHOR_NUM_24_17",
        "발람 신탁 은유는 외부 컨설턴트 리포트·양면 메시지 비유이며, 예언이 아님.",
        [
            n("민수기 22:12", "너는 그 백성을 저주하지 말라", "is_do_not_curse_of", "do not curse — policy constraint", "research_metaphor_policy_constraint"),
            n("민수기 23:20", "내가 받은 명령을 어기고", "is_cannot_beyond_of", "cannot beyond — bounded agent", "research_metaphor_bounded_agent"),
            n("민수기 31:16", "발람의 꾀로", "is_peor_balaam_of", "Peor Balaam — bad advice", "research_metaphor_bad_advice"),
            n("베드로후서 2:15", "발람의 길을 좇아", "is_way_balaam_of", "way Balaam — anti-pattern", "research_metaphor_anti_pattern"),
        ],
    ),
    row(
        "korah_earth",
        "고라 땅 삼킴 (Korah Earth)",
        "민수기 16:32",
        "땅이 그들의 입을 벌려",
        "ANCHOR_NUM_16_32",
        "고라 은유는 권한 난동·즉시 격리 비유이며, 지진이 아님.",
        [
            n("민수기 16:3", "회중이 다 거룩하고", "is_all_holy_of", "all holy — RBAC dispute", "research_metaphor_rbac_dispute"),
            n("민수기 16:40", "이와 같이 제사장이 아닌", "is_not_priest_of", "not priest — unauthorized", "research_metaphor_unauthorized"),
            n("유다서 1:11", "고라의 패역을 따라", "is_korah_rebellion_of", "Korah rebellion — mutiny", "research_metaphor_mutiny"),
            n("시편 106:17", "땅이 갈라져 다스아를", "is_swallowed_dathan_of", "swallowed — instant revoke", "research_metaphor_instant_revoke"),
        ],
    ),
    row(
        "aaron_budding",
        "아론 지팡이 싹 (Aaron Budding Rod)",
        "민수기 17:8",
        "아론의 지팡이에 싹이 나고",
        "ANCHOR_NUM_17_8",
        "싹 난 지팡이 은유는 단일 승자 키·권한 증명 비유이며, 가격이 아님.",
        [
            n("민수기 17:5", "내가 택한 자의 지팡이에", "is_chosen_staff_of", "chosen staff — primary key", "research_metaphor_primary_key"),
            n("히브리서 9:4", "아론의 싹 난 지팡이가", "is_ark_rod_of", "ark rod — vault proof", "research_metaphor_vault_proof"),
            n("이사야 11:1", "이새의 그루터기에서", "is_stump_branch_of", "stump branch — fork winner", "research_metaphor_fork_winner"),
            n("시편 23:4", "주의 지팡이와 막대기가", "is_rod_staff_of", "rod staff — guardrail", "research_metaphor_guardrail"),
        ],
    ),
    row(
        "joshua_stones",
        "여호수아 돌 (Joshua Stones)",
        "여호수아 4:7",
        "이스라엘 백성이 요단강을 건널 때에",
        "ANCHOR_JOS_4_7",
        "기념 돌 은유는 마일스톤 아티팩트·감사 로그 비유이며, 건축이 아님.",
        [
            n("여호수아 4:3", "사람 한 사람씩 돌 하나씩", "is_twelve_stones_of", "twelve stones — shard markers", "research_metaphor_shard_markers"),
            n("여호수아 4:9", "요단 가운데에도 돌 열두 개를", "is_mid_jordan_of", "mid Jordan — dual write proof", "research_metaphor_dual_write_proof"),
            n("여호수아 24:27", "이 돌을 우리에게 증거 삼으라", "is_witness_stone_of", "witness stone — immutable log", "research_metaphor_immutable_log"),
            n("베드로전서 2:5", "살아 있는 돌들 같이", "is_living_stones_of", "living stones — fleet nodes", "research_metaphor_fleet_nodes"),
        ],
    ),
    row(
        "barak_deborah",
        "바락 드보라 (Barak Deborah)",
        "사사기 4:14",
        "일어나라 이 날은 여호와께서",
        "ANCHOR_JDG_4_14",
        "드보라 은유는 공동 온콜·페어 프로그래밍 비유이며, 성별이 아님.",
        [
            n("사사기 4:6", "이스라엘의 하나님 여호와의 명령으로", "is_sent_deborah_of", "sent Deborah — incident commander", "research_metaphor_incident_commander"),
            n("사사기 4:8", "네가 나와 함께 가면", "is_if_you_go_of", "if you go — pair required", "research_metaphor_pair_required"),
            n("사사기 5:31", "사사들의 땅에서", "is_peace_forty_of", "peace forty — stable window", "research_metaphor_stable_window"),
            n("갈라디아서 3:28", "남녀가 없으니", "is_neither_male_of", "neither male — equal role", "research_metaphor_equal_role"),
        ],
    ),
    row(
        "samuel_anointing",
        "사무엘 기름 (Samuel Anointing)",
        "사무엘상 16:13",
        "사무엘이 기름 뿔을 가져다가",
        "ANCHOR_1SA_16_13",
        "기름 부음 은유는 프로덕션 승격·RBAC 부여 비유이며, 종교 의식이 아님.",
        [
            n("사무엘상 3:10", "여호와여 말씀하시옵소서", "is_speak_lord_of", "speak Lord — on-call answer", "research_metaphor_oncall_answer"),
            n("사무엘상 16:7", "사람은 외모를 보거니와", "is_looks_heart_of", "looks heart — hire for skill", "research_metaphor_hire_for_skill"),
            n("시편 2:2", "여호와와 그의 기름부음을 받은 자를", "is_anointed_of", "anointed — prod access", "research_metaphor_prod_access"),
            n("사도행전 13:22", "내 마음에 합한 사람을", "is_man_after_heart_of", "man after heart — good fit", "research_metaphor_good_fit"),
        ],
    ),
    row(
        "david_harp",
        "다윗 수금 (David Harp)",
        "사무엘상 16:23",
        "다윗이 손에 수금을 잡고",
        "ANCHOR_1SA_16_23",
        "수금 은유는 완화 패턴·노이즈 억제 비유이며, 음악 KPI가 아님.",
        [
            n("사무엘상 16:14", "악한 영이 사울에게서", "is_evil_spirit_of", "evil spirit — noisy neighbor", "research_metaphor_noisy_neighbor"),
            n("시편 23:1", "여호와는 나의 목자시니", "is_lord_shepherd_of", "Lord shepherd — SRE guide", "research_metaphor_sre_guide"),
            n("시편 51:10", "내 안에 정한 마음을 창조하시고", "is_clean_heart_of", "clean heart — reset state", "research_metaphor_reset_state"),
            n("아가 2:12", "왕이 식사할 때에", "is_banquet_love_of", "banquet love — calm period", "research_metaphor_calm_period"),
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
