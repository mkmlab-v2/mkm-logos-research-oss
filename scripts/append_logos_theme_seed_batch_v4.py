#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v4, Track B NON_GATING)."""
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
        "fruit_spirit",
        "성령의 열매 (Fruit of Spirit)",
        "갈라디아서 5:22",
        "성령의 열매는 사랑과 기쁨과 화평이니",
        "ANCHOR_GAL_5_22",
        "성령 열매 은유는 팀 문화 KPI·행동 지표 비유이며, 영적 확정이 아님.",
        [
            n("갈라디아서 5:23", "절제와 인내와 자비와", "is_self_control_of", "self control — rate limit culture", "research_metaphor_rate_limit_culture"),
            n("요한복음 15:5", "가지가 포도나무에 붙어 있지 아니하면", "is_branch_vine_of", "branch vine — service mesh attach", "research_metaphor_service_mesh_attach"),
            n("야고보서 3:17", "위에서부터 내려온 지혜는", "is_wisdom_above_of", "wisdom above — platform standards", "research_metaphor_platform_standards"),
            n("에베소서 5:9", "빛의 열매는 모든 덕과", "is_fruit_light_of", "fruit of light — good metrics", "research_metaphor_good_metrics"),
        ],
    ),
    row(
        "revelation_alpha",
        "알파와 오메가 (Alpha Omega)",
        "요한계시록 1:8",
        "나는 알파와 오메가라",
        "ANCHOR_REV_1_8",
        "알파 오메가 은유는 API 수명주기 양끝·버전 경계 비유이며, 가격 신호가 아님.",
        [
            n("요한계시록 22:13", "나는 알파와 오메가요", "is_first_last_of", "first last — v1 and sunset", "research_metaphor_v1_sunset"),
            n("이사야 44:6", "나는 처음이요 나중이니", "is_first_last_god_of", "first last God — sole authority", "research_metaphor_sole_authority"),
            n("요한복음 1:1", "태초에 말씀이 계시니라", "is_word_beginning_of", "word beginning — bootstrap", "research_metaphor_bootstrap"),
            n("히브리서 13:8", "어제나 오늘이나 영원토록", "is_same_yesterday_of", "same forever — stable contract", "research_metaphor_stable_contract"),
        ],
    ),
    row(
        "seven_churches",
        "일곱 교회 (Seven Churches)",
        "요한계시록 1:11",
        "에베소 교회에 보내어 기록하라",
        "ANCHOR_REV_1_11",
        "일곱 교회 은유는 멀티 테넌트 헬스·지역별 감사 비유이며, 종말 예측이 아님.",
        [
            n("요한계시록 2:5", "어디서 떨어졌는지 생각하고", "is_remember_fallen_of", "remember fallen — drift detected", "research_metaphor_drift_detected"),
            n("요한계시록 3:20", "문 밖에 서서 두드리노니", "is_stand_knock_of", "stand knock — pending deploy", "research_metaphor_pending_deploy"),
            n("요한계시록 2:10", "끝까지 충성하라", "is_faithful_until_death_of", "faithful until — SLO streak", "research_metaphor_slo_streak"),
            n("마태복음 18:20", "두 세 사람이 내 이름으로", "is_two_three_gathered_of", "two three gathered — quorum", "research_metaphor_quorum"),
        ],
    ),
    row(
        "four_horsemen",
        "네 말 (Four Horsemen)",
        "요한계시록 6:2",
        "흰 말을 탄 자가 이기기를 원하여",
        "ANCHOR_REV_6_2",
        "네 말 은유는 연쇄 장애 모드·심각도 레벨 비유이며, 시장 사이클이 아님.",
        [
            n("요한계시록 6:4", "붉은 말이 나오매", "is_red_horse_of", "red horse — outage war", "research_metaphor_outage_war"),
            n("요한계시록 6:5", "검은 말이 나오매", "is_black_horse_of", "black horse — cost famine", "research_metaphor_cost_famine"),
            n("요한계시록 6:8", "청황색 말이 나오매", "is_pale_horse_of", "pale horse — death tier", "research_metaphor_death_tier"),
            n("스가랴 6:5", "붉은 말이 나오더라", "is_zechariah_horses_of", "Zechariah horses — patrol agents", "research_metaphor_patrol_agents"),
        ],
    ),
    row(
        "michael_war",
        "미가엘 전쟁 (Michael War)",
        "요한계시록 12:7",
        "천사가 미가엘과 그의 천사들이",
        "ANCHOR_REV_12_7",
        "미가엘 은유는 보안 인시던트·악성 트래픽 방어 비유이며, 실전 매매가 아님.",
        [
            n("유다서 1:9", "미가엘 천사장이 모세의 시체로", "is_michael_dispute_of", "Michael dispute — authz fight", "research_metaphor_authz_fight"),
            n("다니엘 12:1", "큰 환난이 있으리니", "is_great_distress_of", "great distress — major incident", "research_metaphor_major_incident"),
            n("요한계시록 12:9", "큰 용이 내쫓기니", "is_dragon_cast_of", "dragon cast — threat evicted", "research_metaphor_threat_evicted"),
            n("에베소서 6:12", "하늘에 있는 정사와 권세와", "is_wrestle_authorities_of", "wrestle authorities — WAF rules", "research_metaphor_waf_rules"),
        ],
    ),
    row(
        "whale_swallow",
        "큰 물고기 (Whale Swallow)",
        "요나 1:17",
        "여호와께서 큰 물고기를 예비하사",
        "ANCHOR_JON_1_17",
        "큰 물고기 은유는 격리 샌드박스·롤백 버퍼 비유이며, 생물학이 아님.",
        [
            n("요나 2:1", "물고기 뱃속에서 요나가", "is_belly_prayed_of", "belly prayed — incident bridge", "research_metaphor_incident_bridge"),
            n("요나 2:10", "여호와께서 물고기에게 말씀하시매", "is_vomited_dry_of", "vomited dry — released from hold", "research_metaphor_released_from_hold"),
            n("마태복음 12:40", "요나가 삼일 밤낮을", "is_three_days_of", "three days — max outage window", "research_metaphor_max_outage_window"),
            n("요나 1:3", "다시스로 도망하려", "is_fled_tarshish_of", "fled — route misconfig", "research_metaphor_route_misconfig"),
        ],
    ),
    row(
        "elijah_whirlwind",
        "엘리야 회오리 (Elijah Whirlwind)",
        "열왕기하 2:11",
        "불보루와 불말거리가 하늘로",
        "ANCHOR_2KI_2_11",
        "회오리 은유는 온콜 인수·급격 핸드오프 비유이며, 날씨가 아님.",
        [
            n("열왕기하 2:9", "감복이 배나지 않게 하옵소서", "is_double_portion_of", "double portion — 2x pager", "research_metaphor_double_pager"),
            n("열왕기하 2:14", "엘리야의 옷을 치매", "is_struck_jordan_of", "strike Jordan — repeat failover", "research_metaphor_repeat_failover"),
            n("말라기 4:5", "엘리야를 너희에게 보내리라", "is_elijah_sent_of", "Elijah sent — mentor returns", "research_metaphor_mentor_returns"),
            n("히브리서 11:5", "에녹은 믿음으로 옮기웠으니", "is_translated_of", "translated — clean exit", "research_metaphor_clean_exit"),
        ],
    ),
    row(
        "gehazi_leprosy",
        "게하시 문둥병 (Gehazi Leprosy)",
        "열왕기하 5:27",
        "게하시에게서 나가서 문둥병이 되어",
        "ANCHOR_2KI_5_27",
        "게하시 은유는 권한 남용·감사 실패 징계 비유이며, 의료가 아님.",
        [
            n("열왕기하 5:20", "내 주인이 이 시리아 사람 나아만을", "is_gehazi_thought_of", "Gehazi thought — side deal", "research_metaphor_side_deal"),
            n("열왕기하 5:26", "내 마음이 너와 함께 있지 아니하냐", "is_not_go_thy_of", "not go with — policy violation", "research_metaphor_policy_violation"),
            n("잠언 28:20", "충성된 자는 복이 많으려니와", "is_faithful_abounds_of", "faithful abounds — trust reward", "research_metaphor_trust_reward"),
            n("고린도전서 5:13", "악한 자는 너희 가운데서", "is_remove_wicked_of", "remove wicked — revoke access", "research_metaphor_revoke_access"),
        ],
    ),
    row(
        "uzziah_pride",
        "웃시야 교만 (Uzziah Pride)",
        "역대하 26:19",
        "그 이마에 문둥병이 나서",
        "ANCHOR_2CH_26_19",
        "웃시야 은유는 권한 상승·프로덕션 직접 개입 비유이며, 정치가 아님.",
        [
            n("역대하 26:16", "권능을 얻으매 그 마음이 교만하여", "is_pride_strong_of", "pride when strong — hubris scale", "research_metaphor_hubris_scale"),
            n("역대하 26:21", "웃시야 왕은 죽는 날까지", "is_isolated_leper_of", "isolated leper — account quarantine", "research_metaphor_account_quarantine"),
            n("잠언 16:18", "교만은 패망의 선봉이요", "is_pride_before_fall_of", "pride before fall — incident precursor", "research_metaphor_incident_precursor"),
            n("이사야 6:1", "웃시야 왕이 죽던 해에", "is_year_king_died_of", "king died year — leadership transition", "research_metaphor_leadership_transition"),
        ],
    ),
    row(
        "solomon_idols",
        "솔로몬 우상 (Solomon Idols)",
        "열왕기상 11:4",
        "그 마음이 그의 하나님 여호와를 떠나",
        "ANCHOR_1KI_11_4",
        "솔로몬 우상 은유는 기술 부채·다중 벤더 락인 비유이며, 종교 단정이 아님.",
        [
            n("열왕기상 11:11", "이 일을 행하여 내 계명을", "is_tore_kingdom_of", "tore kingdom — split org", "research_metaphor_split_org"),
            n("열왕기상 11:33", "이스라엘을 그의 아들에게서", "is_rent_kingdom_of", "rent kingdom — divest shard", "research_metaphor_divest_shard"),
            n("신명기 17:17", "아내를 많이 두지 말지니", "is_not_many_wives_of", "not many wives — limit integrations", "research_metaphor_limit_integrations"),
            n("고린도전서 10:14", "우상 숭배를 피하라", "is_flee_idolatry_of", "flee idolatry — one platform", "research_metaphor_one_platform"),
        ],
    ),
    row(
        "rehoboam_split",
        "르호보암 분열 (Rehoboam Split)",
        "열왕기상 12:16",
        "이스라엘이 왕에게 돌아가 자기 장막으로",
        "ANCHOR_1KI_12_16",
        "르호보암 은유는 조직 분리·하드 포크 비유이며, 시장 분할이 아님.",
        [
            n("열왕기상 12:4", "이제 왕의 짐을 가볍게 하소서", "is_lighten_burden_of", "lighten burden — reduce toil", "research_metaphor_reduce_toil"),
            n("열왕기상 12:11", "내 아버지가 너희를 채찍으로", "is_heavier_yoke_of", "heavier yoke — bad leadership", "research_metaphor_bad_leadership"),
            n("열왕기상 12:20", "온 이스라엘이 유다를 따르지 아니하고", "is_israel_followed_of", "Israel followed — tenant split", "research_metaphor_tenant_split"),
            n("고린도전서 1:10", "다 같은 말을 하고", "is_same_mind_of", "same mind — avoid schism", "research_metaphor_avoid_schism"),
        ],
    ),
    row(
        "ahab_vineyard",
        "아합 포도원 (Ahab Vineyard)",
        "열왕기상 21:19",
        "개들이 나볼의 피를 핥을 것이라",
        "ANCHOR_1KI_21_19",
        "나볼 포도원 은유는 자산 강탈·불공정 인수 비유이며, M&A가 아님.",
        [
            n("열왕기상 21:3", "여호와께서 내게 금하사", "is_lord_forbid_of", "Lord forbid — policy block", "research_metaphor_policy_block"),
            n("열왕기상 21:7", "이스라엘의 왕이여 일어나", "is_jezebel_wrote_of", "Jezebel wrote — exec override", "research_metaphor_exec_override"),
            n("열왕기상 21:13", "나볼이 하나님과 왕을", "is_cursed_god_king_of", "cursed — framed incident", "research_metaphor_framed_incident"),
            n("이사야 5:7", "그의 기뻐하시는 포도원", "is_vineyard_beloved_of", "beloved vineyard — core asset", "research_metaphor_core_asset"),
        ],
    ),
    row(
        "jezebel_baal",
        "이세벨 바알 (Jezebel Baal)",
        "열왕기상 18:19",
        "이스라엘의 모든 선지자를",
        "ANCHOR_1KI_18_19",
        "이세벨 은유는 거짓 메트릭·이단 교육 비유이며, 성별 정치가 아님.",
        [
            n("열왕기상 16:31", "시드론의 아들 에담방의 딸 이세벨을", "is_married_jezebel_of", "married Jezebel — bad merger", "research_metaphor_bad_merger"),
            n("열왕기상 19:2", "내일 이맘때 네 생명도", "is_swear_life_of", "swear life — death threat", "research_metaphor_death_threat"),
            n("계시록 2:20", "자칭 선지자 이세벨이라 하는", "is_jezebel_tolerates_of", "Jezebel tolerates — ignore alerts", "research_metaphor_ignore_alerts"),
            n("열왕기상 18:40", "바알의 선지자들을 잡으매", "is_slain_prophets_of", "slain prophets — purge false", "research_metaphor_purge_false"),
        ],
    ),
    row(
        "mantle_pass",
        "외투 전수 (Mantle Pass)",
        "열왕기하 2:13",
        "엘리야의 외투를 집어 들고",
        "ANCHOR_2KI_2_13",
        "외투 전수 은유는 온콜 로테이션·권한 이양 비유이며, 패션이 아님.",
        [
            n("열왕기상 19:19", "엘리야가 외투를 던지매", "is_cast_mantle_of", "cast mantle — assign role", "research_metaphor_assign_role"),
            n("열왕기하 2:14", "엘리야의 옷을 치매", "is_struck_water_of", "strike water — same credentials", "research_metaphor_same_credentials"),
            n("시편 133:2", "아론의 머리에", "is_dew_hermon_of", "dew Hermon — shared blessing", "research_metaphor_shared_blessing"),
            n("빌립보서 2:5", "그리스도 예수 안에 있는", "is_mind_christ_of", "mind Christ — runbook culture", "research_metaphor_runbook_culture"),
        ],
    ),
    row(
        "naaman_servant",
        "나아만 종 (Naaman Servant)",
        "열왕기하 5:13",
        "내 아버지여 선지자가 큰 일을",
        "ANCHOR_2KI_5_13",
        "종 은유는 주니어 설득·에스컬레이션 전 비유이며, HR이 아님.",
        [
            n("열왕기하 5:2", "군대 장관 나아만은", "is_captain_syria_of", "captain Syria — VIP tenant", "research_metaphor_vip_tenant"),
            n("열왕기하 5:11", "손을 흔들어 나을 줄", "is_expected_wave_of", "expected wave — magic fix", "research_metaphor_magic_fix"),
            n("열왕기하 5:14", "요단 강에 일곱 번", "is_seven_dips_of", "seven dips — retry loop", "research_metaphor_retry_loop"),
            n("누가복음 4:27", "수리아 사람 나아만", "is_gentile_healed_of", "gentile healed — edge case win", "research_metaphor_edge_case_win"),
        ],
    ),
    row(
        "pilate_wash",
        "빌라도 씻음 (Pilate Wash)",
        "마태복음 27:24",
        "물을 가져다가 무리 앞에서",
        "ANCHOR_MAT_27_24",
        "빌라도 은유는 책임 회피·감사 서명 거부 비유이며, 법률 자문이 아님.",
        [
            n("마태복음 27:26", "예수를 채찍에 맞기신 후에", "is_scourged_delivered_of", "scourged delivered — shipped anyway", "research_metaphor_shipped_anyway"),
            n("요한복음 19:4", "내가 그에게서 죄를 찾지 못하겠나이다", "is_no_fault_of", "no fault — clean audit", "research_metaphor_clean_audit"),
            n("시편 26:6", "내 손을 씻고", "is_wash_hands_of", "wash hands — disclaimer only", "research_metaphor_disclaimer_only"),
            n("야고보서 4:17", "선을 행하지 아니하면", "is_sins_omission_of", "sin omission — knew and skipped", "research_metaphor_knew_and_skipped"),
        ],
    ),
    row(
        "crown_thorns",
        "가시 면류관 (Crown of Thorns)",
        "마태복음 27:29",
        "가시 면류관을 엮어 그의 머리에",
        "ANCHOR_MAT_27_29",
        "가시 면류관 은유는 모의 배포·적대적 테스트 비유이며, 수익이 아님.",
        [
            n("마태복음 27:31", "가시 면류관을 벗기고", "is_mocked_scourged_of", "mocked scourged — chaos drill", "research_metaphor_chaos_drill"),
            n("요한복음 19:2", "군병들이 가시 면류관을", "is_soldiers_platted_of", "soldiers platted — red team", "research_metaphor_red_team"),
            n("이사야 53:3", "멸시받아 사람에게 끊어진", "is_despised_rejected_of", "despised rejected — outage blame", "research_metaphor_outage_blame"),
            n("히브리서 2:9", "죽음의 고통을 맛보심으로", "is_taste_death_of", "taste death — drill pain", "research_metaphor_drill_pain"),
        ],
    ),
    row(
        "ruth_kinsman",
        "룻 친족 (Ruth Kinsman)",
        "룻기 3:9",
        "나의 친족 되시기를 원하나이다",
        "ANCHOR_RUT_3_9",
        "룻 친족 은유는 테넌트 온보딩·커버리지 확장 비유이며, M&A가 아님.",
        [
            n("룻기 1:16", "당신이 가시는 곳에 나도 가며", "is_where_you_go_of", "where you go — follow primary", "research_metaphor_follow_primary"),
            n("룻기 2:2", "이삭을 베어 수금하리이다", "is_glean_field_of", "glean field — read replica", "research_metaphor_read_replica"),
            n("룻기 4:14", "여호와께서 생명의 구원자를", "is_redeemer_given_of", "redeemer given — sponsor assigned", "research_metaphor_sponsor_assigned"),
            n("갈라디아서 3:28", "유대인이나 헬라인이나", "is_neither_jew_of", "neither Jew — equal access", "research_metaphor_equal_access"),
        ],
    ),
    row(
        "gideon_torches",
        "기드온 횃불 (Gideon Torches)",
        "사사기 7:20",
        "횃불을 부수고 외치되",
        "ANCHOR_JDG_7_20",
        "횃불 은유는 야간 릴리스·동시 블라스트 비유이며, 군사 작전이 아님.",
        [
            n("사사기 7:7", "이 물을 핥는 자 삼백 명을", "is_three_hundred_of", "three hundred — small fleet", "research_metaphor_small_fleet"),
            n("사사기 7:16", "횃불을 항아리 속에 두고", "is_lamps_jars_of", "lamps in jars — hidden canary", "research_metaphor_hidden_canary"),
            n("사사기 7:22", "칼을 피하여 도망하며", "is_fled_swords_of", "fled swords — panic routing", "research_metaphor_panic_routing"),
            n("히브리서 11:32", "기드온", "is_faith_hall_of", "faith hall — underdog win", "research_metaphor_underdog_win"),
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
