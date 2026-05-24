#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v2, Track B NON_GATING)."""
from __future__ import annotations

import json
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
        "tower_babel",
        "바벨 탑 (Tower of Babel)",
        "창세기 11:4",
        "탑 꼭대기가 하늘에 닿게 하자",
        "ANCHOR_GEN_11_4",
        "바벨 은유는 스키마 분열·언어 불일치 비유이며, 시장 붕괴 예측이 아님.",
        [
            n("창세기 11:7", "언어를 혼잡하게 하사", "is_confuse_language_of", "split dialects — API incompatibility", "research_metaphor_api_incompat"),
            n("창세기 11:8", "거기서 그들을 흩으셨으므로", "is_scattered_of", "scatter tenants — multi-region fork", "research_metaphor_scatter_tenants"),
            n("신명기 32:8", "경계를 나누셨고", "is_set_boundaries_of", "partition map — shard boundaries", "research_metaphor_shard_boundaries"),
            n("사도행전 2:6", "각각 자기 방언으로", "is_own_tongue_of", "Pentecost undo — unified protocol", "research_metaphor_unified_protocol"),
        ],
    ),
    row(
        "abel_blood",
        "아벨 피 (Abel Blood)",
        "창세기 4:10",
        "네가 한 일이 무엇이냐",
        "ANCHOR_GEN_4_10",
        "아벨 은유는 감사 로그·증거 잔존 비유이며, 형사 단정이 아님.",
        [
            n("창세기 4:4", "여호와께서 아벨과 그 예물을", "is_regarded_offering_of", "accepted deploy — green build", "research_metaphor_green_build"),
            n("히브리서 11:4", "의로운 자라 하심을", "is_righteous_named_of", "righteous label — audit pass", "research_metaphor_audit_pass"),
            n("히브리서 12:24", "아벨의 피보다 나은 피가", "is_better_blood_of", "better witness — stronger evidence", "research_metaphor_stronger_evidence"),
            n("요한일서 3:12", "악한 자에게 속하라", "is_of_evil_one_of", "Cain path — toxic actor", "research_metaphor_toxic_actor"),
        ],
    ),
    row(
        "cain_mark",
        "가인 표 (Cain Mark)",
        "창세기 4:15",
        "가인에게 표를 주사",
        "ANCHOR_GEN_4_15",
        "가인 표 은유는 격리 태그·제한 계정 비유이며, 투자 신호가 아님.",
        [
            n("창세기 4:12", "땅이 그대에게 효력을 주지 아니하리니", "is_cursed_ground_of", "no yield — sandbox only", "research_metaphor_sandbox_only"),
            n("창세기 4:16", "에덴 동쪽 누드 땅에 거하니라", "is_went_nod_of", "exile region — restricted VPC", "research_metaphor_restricted_vpc"),
            n("유다서 1:11", "가인의 길에 들어가서", "is_way_cain_of", "anti-pattern cite — blocked path", "research_metaphor_blocked_path"),
            n("요한일서 3:12", "형제를 죽였으매", "is_slew_brother_of", "internal harm — insider threat", "research_metaphor_insider_threat"),
        ],
    ),
    row(
        "enoch_walk",
        "에녹 동행 (Enoch Walk)",
        "창세기 5:24",
        "에녹은 하나님과 동행하더니",
        "ANCHOR_GEN_5_24",
        "에녹 은유는 장기 무사고 운영·연속 준수 비유이며, 수익 보장이 아님.",
        [
            n("히브리서 11:5", "죽음을 보지 않고 옮기웠으니", "is_translated_of", "clean exit — zero-downtime handoff", "research_metaphor_zero_downtime_handoff"),
            n("미가 6:8", "정의를 행하며 인애를 베풀며", "is_do_justly_of", "walk humbly — SLO culture", "research_metaphor_slo_culture"),
            n("아모스 3:3", "두 사람이 동의하지 않으면", "is_agree_walk_of", "must align — paired deploy", "research_metaphor_paired_deploy"),
            n("갈라디아서 5:16", "성령을 따라 행하라", "is_walk_spirit_of", "follow spirit — policy guided", "research_metaphor_policy_guided"),
        ],
    ),
    row(
        "melchizedek_bread",
        "멜기세덱 빵 (Melchizedek Bread)",
        "창세기 14:18",
        "떡과 포도주를 가지고",
        "ANCHOR_GEN_14_18",
        "멜기세덱 은유는 게스트 권한·임시 승격 비유이며, 결제 승인이 아님.",
        [
            n("히브리서 7:1", "살렘 왕 멜기세덱이", "is_king_salem_of", "external king — vendor broker", "research_metaphor_vendor_broker"),
            n("히브리서 7:3", "아버지도 어머니도 없이", "is_without_genealogy_of", "no lineage — system account", "research_metaphor_system_account"),
            n("시편 110:4", "멜기세덱의 반차를 따라", "is_order_melchizedek_of", "priest order — elevated role", "research_metaphor_elevated_role"),
            n("히브리서 5:6", "멜기세덱의 반차를 따라", "is_after_order_of", "same order — inherited RBAC", "research_metaphor_inherited_rbac"),
        ],
    ),
    row(
        "abraham_sacrifice",
        "아브라함 번제 (Abraham Sacrifice)",
        "창세기 22:8",
        "하나님이 자기를 위하여 양을 예비하시리라",
        "ANCHOR_GEN_22_8",
        "이삭 은유는 드릴·대체 리소스 비유이며, 실제 희생 확정이 아님.",
        [
            n("창세기 22:12", "네가 네 아들을 아끼지 아니하였으니", "is_did_not_withhold_of", "drill passed — readiness proven", "research_metaphor_readiness_proven"),
            n("창세기 22:13", "숫양을 대신하여", "is_ram_instead_of", "substitute — failover target", "research_metaphor_failover_target"),
            n("히브리서 11:17", "믿음으로 아브라함이", "is_by_faith_of", "faith drill — chaos test", "research_metaphor_chaos_test"),
            n("야고보서 2:21", "행함으로 온전하게 되었으니", "is_works_complete_of", "action proved — runbook executed", "research_metaphor_runbook_executed"),
        ],
    ),
    row(
        "isaac_wells",
        "이삭 우물 (Isaac Wells)",
        "창세기 26:22",
        "여호와께서 우리를 위하여 넓게 하셨다",
        "ANCHOR_GEN_26_22",
        "우물 은유는 리소스 풀·용량 확보 비유이며, 유가 예측이 아님.",
        [
            n("창세기 26:15", "이삭의 아버지 아브라함의 때에", "is_stopped_wells_of", "stopped wells — capacity blocked", "research_metaphor_capacity_blocked"),
            n("창세기 26:18", "아버지 아브라함의 때에 팠던", "is_reopened_wells_of", "reopen legacy — restore pools", "research_metaphor_restore_pools"),
            n("요한복음 4:14", "영원히 솟아나는 샘물", "is_spring_eternal_of", "living water — autoscale", "research_metaphor_autoscale"),
            n("잠언 5:15", "네 샘에서 물을 마시라", "is_drink_own_well_of", "own well — private cache", "research_metaphor_private_cache"),
        ],
    ),
    row(
        "pharaoh_hardened",
        "바로 완악 (Pharaoh Hardened)",
        "출애굽기 9:12",
        "여호와께서 바로의 마음을 굳게 하시고",
        "ANCHOR_EXO_9_12",
        "바로 은유는 변경 거부·기술 부채 고착 비유이며, 정치 예측이 아님.",
        [
            n("출애굽기 5:2", "여호와가 누구냐", "is_who_is_lord_of", "deny owner — ignore platform", "research_metaphor_ignore_platform"),
            n("출애굽기 8:15", "바로가 마음을 완악하게 하고", "is_hardened_again_of", "relapse harden — rollback refused", "research_metaphor_rollback_refused"),
            n("로마서 9:18", "원하시는 자를 긍휼히", "is_mercy_wills_of", "sovereign override — exec decision", "research_metaphor_exec_decision"),
            n("잠언 29:1", "자주 책망을 받고도", "is_often_reproved_of", "ignored warnings — alert fatigue", "research_metaphor_alert_fatigue"),
        ],
    ),
    row(
        "plagues_egypt",
        "애굽 재앙 (Plagues of Egypt)",
        "출애굽기 7:5",
        "애굽 사람들이 여호와인 줄 알리라",
        "ANCHOR_EXO_7_5",
        "재앙 은유는 연쇄 장애·단계적 격리 비유이며, 시장 폭락이 아님.",
        [
            n("출애굽기 8:6", "개구리가 죽어 악취가", "is_frogs_died_of", "stink after fix — debt cleanup", "research_metaphor_debt_cleanup"),
            n("출애굽기 10:21", "애굽 땅에 짙은 어두움이", "is_darkness_three_of", "three day outage — major incident", "research_metaphor_major_incident"),
            n("출애굽기 12:29", "밤중에 여호와께서", "is_midnight_strike_of", "midnight deploy — off-hours cut", "research_metaphor_offhours_cut"),
            n("시편 78:43", "징표와 이적을 애굽에", "is_signs_egypt_of", "signs logged — audit trail", "research_metaphor_audit_trail"),
        ],
    ),
    row(
        "pillar_cloud",
        "구름 기둥 (Pillar Cloud)",
        "출애굽기 13:21",
        "낮에는 구름 기둥으로",
        "ANCHOR_EXO_13_21",
        "기둥 은유는 리더 선행·트래픽 라우팅 비유이며, 날씨 알파가 아님.",
        [
            n("출애굽기 14:19", "구름 기둥이 그들 앞에서", "is_moved_behind_of", "rear guard — WAF behind", "research_metaphor_waf_behind"),
            n("출애굽기 40:38", "구름이 회막 위에 덮였으므로", "is_cloud_covered_of", "covered tabernacle — mesh overlay", "research_metaphor_mesh_overlay"),
            n("시편 105:39", "구름으로 가리우고", "is_cloud_cover_of", "cover march — canary shield", "research_metaphor_canary_shield"),
            n("고린도전서 10:1", "구름 아래로 지나고", "is_under_cloud_of", "all under cloud — shared LB", "research_metaphor_shared_lb"),
        ],
    ),
    row(
        "manna_sabbath",
        "만나 안식 (Manna Sabbath)",
        "출애굽기 16:26",
        "안식일에는 없으리라",
        "ANCHOR_EXO_16_26",
        "만나 안식 은유는 변경 동결 창·배포 금지 비유이며, 수익 휴일이 아님.",
        [
            n("출애굽기 16:4", "하루 분씩 거두게 하리라", "is_daily_gather_of", "daily quota — rate limit", "research_metaphor_rate_limit"),
            n("출애굽기 16:20", "이튿날 벌레가 들어가", "is_bred_worms_of", "hoard rots — cache TTL", "research_metaphor_cache_ttl"),
            n("신명기 8:3", "사람이 떡으로만 사는 것이 아니라", "is_not_bread_alone_of", "not bread only — multi signal", "research_metaphor_multi_signal"),
            n("요한복음 6:49", "광야에서 만나를 먹었어도", "is_ate_manna_of", "ancestors ate — legacy quota", "research_metaphor_legacy_quota"),
        ],
    ),
    row(
        "korah_rebellion",
        "고라 반역 (Korah Rebellion)",
        "민수기 16:32",
        "땅이 그들의 입을 벌려",
        "ANCHOR_NUM_16_32",
        "고라 은유는 권한 난동·스플릿 브레인 비유이며, 매매 신호가 아님.",
        [
            n("민수기 16:3", "회중이 다 거룩하고", "is_all_holy_of", "claim equal role — RBAC dispute", "research_metaphor_rbac_dispute"),
            n("민수기 16:40", "이와 같이 제사장이 아닌", "is_not_priest_of", "unauthorized altar — shadow API", "research_metaphor_shadow_api"),
            n("유다서 1:11", "고라의 패역을 따라", "is_rebellion_korah_of", "mutiny pattern — split vote", "research_metaphor_split_vote"),
            n("시편 106:17", "땅이 갈라져 다스아를", "is_earth_swallowed_of", "swallowed — instant revoke", "research_metaphor_instant_revoke"),
        ],
    ),
    row(
        "aaron_rod",
        "아론 지팡이 (Aaron Rod)",
        "민수기 17:8",
        "아론의 지팡이가 싹을 내고",
        "ANCHOR_NUM_17_8",
        "지팡이 은유는 단일 승자 키·권한 증명 비유이며, 가격 신호가 아님.",
        [
            n("민수기 17:5", "내가 택한 자의 지팡이에", "is_chosen_staff_of", "chosen staff — primary key", "research_metaphor_primary_key"),
            n("히브리서 9:4", "아론의 싹 난 지팡이가", "is_ark_rod_of", "in ark — vault secret", "research_metaphor_vault_secret"),
            n("시편 23:4", "주의 지팡이와 막대기가", "is_rod_staff_of", "comfort rod — guardrail", "research_metaphor_guardrail"),
            n("이사야 11:1", "이새의 그루터기에서", "is_stump_sprout_of", "sprout from stump — fork winner", "research_metaphor_fork_winner"),
        ],
    ),
    row(
        "canaan_spies",
        "가나안 정탐 (Canaan Spies)",
        "민수기 13:30",
        "우리가 올라가서 그 땅을 취하자",
        "ANCHOR_NUM_13_30",
        "정탐 은유는 POC 보고·리스크 편향 비유이며, 진입 타이밍이 아님.",
        [
            n("민수기 13:32", "백성이 우리보다 강하니", "is_too_strong_of", "fear report — pessimistic KPI", "research_metaphor_pessimistic_kpi"),
            n("민수기 14:24", "마음이 달라 순종하며", "is_different_spirit_of", "Caleb spirit — canary pass", "research_metaphor_canary_pass"),
            n("여호수아 2:1", "정탐꾼 두 사람을", "is_sent_spies_of", "send spies — staging probe", "research_metaphor_staging_probe"),
            n("히브리서 3:19", "믿지 못하므로 들어가지 못함을", "is_could_not_enter_of", "unbelief block — gate failed", "research_metaphor_gate_failed"),
        ],
    ),
    row(
        "ark_covenant",
        "언약궤 (Ark of Covenant)",
        "여호수아 3:13",
        "언약궤를 메는 제사장들의 발바닥이",
        "ANCHOR_JOS_3_13",
        "언약궤 은유는 핵심 상태·싱글 리더 비유이며, 보물 가격이 아님.",
        [
            n("신명기 10:5", "내가 만든 궤에 넣으니라", "is_put_ark_of", "state in box — durable store", "research_metaphor_durable_store"),
            n("사무엘상 4:11", "언약궤가 빼앗기고", "is_ark_captured_of", "captured — primary lost", "research_metaphor_primary_lost"),
            n("시편 132:8", "주의 계실 곳에 들어가사", "is_enter_rest_of", "resting place — home region", "research_metaphor_home_region"),
            n("히브리서 9:4", "금 향로와 언약궤가", "is_holiest_ark_of", "holiest — tier zero data", "research_metaphor_tier_zero_data"),
        ],
    ),
    row(
        "elijah_raven",
        "엘리야 까마귀 (Elijah Raven)",
        "열왕기상 17:6",
        "까마귀들이 아침과 저녁으로",
        "ANCHOR_1KI_17_6",
        "까마귀 은유는 예기치 않은 공급·백업 채널 비유이며, 수익이 아님.",
        [
            n("열왕기상 17:4", "시냇물을 마시게 하시고", "is_brook_drink_of", "brook supply — side channel", "research_metaphor_side_channel"),
            n("열왕기상 17:14", "가루통의 가루와 병의 기름이", "is_barrel_not_fail_of", "jar not fail — quota holds", "research_metaphor_quota_holds"),
            n("열왕기상 17:16", "여호와의 말씀대로", "is_word_lord_of", "per word — contract SLO", "research_metaphor_contract_slo"),
            n("누가복음 4:25", "엘리야 때에 하늘이 닫힌지", "is_heaven_shut_of", "drought season — cost freeze", "research_metaphor_cost_freeze"),
        ],
    ),
    row(
        "elisha_bones",
        "엘리사 뼈 (Elisha Bones)",
        "열왕하 13:21",
        "엘리사의 뼈에 닿은 자가 살아나",
        "ANCHOR_2KI_13_21",
        "뼈 은유는 레거시 터치·핫스왑 복구 비유이며, 의료가 아님.",
        [
            n("열왕하 2:9", "감복이 배나지 않게 하옵소서", "is_double_spirit_of", "double spirit — 2x capacity", "research_metaphor_double_capacity"),
            n("열왕하 2:14", "엘리야의 옷을 치매", "is_struck_water_of", "strike water — repeat ritual", "research_metaphor_repeat_ritual"),
            n("열왕하 4:35", "아이가 일어나", "is_child_sneezed_of", "revive child — incident recovered", "research_metaphor_incident_recovered"),
            n("히브리서 11:35", "죽은 자 가운데서 다시 살아나는", "is_raised_dead_of", "raised dead — DR success", "research_metaphor_dr_success"),
        ],
    ),
    row(
        "hezekiah_sundial",
        "히스기야 해시계 (Hezekiah Sundial)",
        "이사야 38:8",
        "아하스의 해시계에 해가 열 도를",
        "ANCHOR_ISA_38_8",
        "해시계 은유는 시간 롤백·클럭 스큐 비유이며, 타이밍 매매가 아님.",
        [
            n("이사야 38:17", "내 영혼을 잔물 속에서 건지셨나이다", "is_pit_preserve_of", "pit preserve — save from outage", "research_metaphor_save_from_outage"),
            n("이사야 39:1", "병 낫고 난 후에", "is_after_recovery_of", "after recovery — postmortem gift", "research_metaphor_postmortem_gift"),
            n("여호수아 10:13", "해가 멈추고", "is_sun_stood_of", "sun stood — freeze window", "research_metaphor_freeze_window"),
            n("아모스 8:9", "해가 정오에 지게 하리라", "is_dark_noon_of", "dark noon — daylight savings bug", "research_metaphor_dst_bug"),
        ],
    ),
    row(
        "josiah_book",
        "요시야 율법책 (Josiah Book)",
        "열왕하 22:11",
        "율법책의 말씀을 듣고",
        "ANCHOR_2KI_22_11",
        "요시야 은유는 잃어버린 SSOT 재발견 비유이며, 규제 예측이 아님.",
        [
            n("열왕하 22:8", "여호와의 전에서 율법책을", "is_found_book_of", "found book — repo archaeology", "research_metaphor_repo_archaeology"),
            n("열왕하 23:3", "언약의 말씀대로 행하리라", "is_stood_pillar_of", "renew covenant — policy refresh", "research_metaphor_policy_refresh"),
            n("역대하 34:19", "율법책의 말씀을 듣고", "is_heard_words_of", "heard words — read the runbook", "research_metaphor_read_runbook"),
            n("예레미야 1:2", "아몬의 아들 요시야의 해에", "is_josiah_days_of", "Josiah era — legacy audit", "research_metaphor_legacy_audit"),
        ],
    ),
    row(
        "jeremiah_potter",
        "예레미야 토기장 (Jeremiah Potter)",
        "예레미야 18:6",
        "이스라엘 집을 행함 같이 행할 수 있음이라",
        "ANCHOR_JER_18_6",
        "토기장 은유는 리팩터·재구성 권한 비유이며, 시장 재형성이 아님.",
        [
            n("예레미야 18:4", "토기장이 만드는 대로", "is_as_potter_wills_of", "as potter wills — architect owns", "research_metaphor_architect_owns"),
            n("예레미야 18:8", "그 나라가 내 앞에서 떠날 때", "is_if_nation_repents_of", "if repent — rollback plan", "research_metaphor_rollback_plan"),
            n("로마서 9:21", "토기장이 진흙 한 덩이로", "is_clay_same_of", "same clay — shared codebase", "research_metaphor_shared_codebase"),
            n("이사야 64:8", "우리는 진흙이요 주는 토기장이시니", "is_we_clay_of", "we clay — tenant shape", "research_metaphor_tenant_shape"),
        ],
    ),
]


def main() -> int:
    import re

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
