#!/usr/bin/env python3
"""Append unique Logos theme seeds (batch v3, Track B NON_GATING)."""
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
        "micah_swords",
        "미가 칼 (Micah Swords)",
        "미가 4:3",
        "칼을 보습으로, 창을 낫으로",
        "ANCHOR_MIC_4_3",
        "미가 칼 은유는 공격 표면 축소·비무장화 비유이며, 군사 예측이 아님.",
        [
            n("미가 6:8", "정의를 행하며 인애를 베풀며", "is_do_justly_of", "do justly — fairness SLO", "research_metaphor_fairness_slo"),
            n("이사야 2:4", "칼을 보습으로", "is_swords_plowshares_of", "plowshares — decommission weapons", "research_metaphor_decommission"),
            n("요엘 3:10", "보습을 칼로", "is_plowshares_swords_of", "reverse — rearm for incident", "research_metaphor_rearm_incident"),
            n("잠언 20:3", "다툼을 멀리하는 것이", "is_avoid_strife_of", "avoid strife — no flame war", "research_metaphor_no_flame_war"),
        ],
    ),
    row(
        "nahum_nineveh",
        "나훔 니느웨 (Nahum Nineveh)",
        "나훔 1:8",
        "대홍수로 그 처소를 물리치시리라",
        "ANCHOR_NAH_1_8",
        "니느웨 은유는 거대 테넌트 붕괴·청산 비유이며, 시장 폭락이 아님.",
        [
            n("나훔 2:6", "강문들이 열리고", "is_gates_opened_of", "gates open — perimeter breach", "research_metaphor_perimeter_breach"),
            n("나훔 3:19", "네 패망이 즐겁지 아니하리라", "is_no_comfort_of", "no comfort — hard postmortem", "research_metaphor_hard_postmortem"),
            n("요나 3:4", "사십 일이면 니느웨가 무너지리라", "is_forty_days_of", "grace window — SLA extension", "research_metaphor_sla_extension"),
            n("스바냐 2:13", "여호와의 손이 너를 치리라", "is_hand_against_of", "hand against — account suspended", "research_metaphor_account_suspended"),
        ],
    ),
    row(
        "zephaniah_day",
        "스바냐 날 (Zephaniah Day)",
        "스바냐 1:14",
        "여호와의 크고 심한 날이 가까웠나니",
        "ANCHOR_ZEP_1_14",
        "스바냐 은유는 메이저 릴리스 마감·감사의 날 비유이며, 타이밍 매매가 아님.",
        [
            n("스바냐 1:18", "여호와의 진노의 날에", "is_wrath_day_of", "wrath day — freeze deploy", "research_metaphor_freeze_deploy"),
            n("스바냐 3:17", "너를 기뻐하시며", "is_rejoices_over_of", "rejoice after — green retrospective", "research_metaphor_green_retro"),
            n("아모스 5:18", "여호와의 날이 어찌 너희에게 어두움이", "is_day_darkness_of", "expected light — failed launch", "research_metaphor_failed_launch"),
            n("요엘 2:31", "큰 두려운 여호와의 날이", "is_terrible_day_of", "terrible day — P0 incident", "research_metaphor_p0_incident"),
        ],
    ),
    row(
        "haggai_temple",
        "학개 성전 (Haggai Temple)",
        "학개 1:8",
        "성전에 올라가서 건축하라",
        "ANCHOR_HAG_1_8",
        "학개 은유는 핵심 서비스 재건·우선순위 복구 비유이며, 부동산가 아님.",
        [
            n("학개 2:9", "이 성전의 나중 영광이", "is_latter_glory_of", "latter glory — v2 better", "research_metaphor_v2_better"),
            n("학개 1:6", "먹어도 배부르지 못하며", "is_not_satisfied_of", "not satisfied — leaky bucket", "research_metaphor_leaky_bucket"),
            n("에스겔 37:27", "내 장막이 그들 가운데에", "is_tabernacle_among_of", "tabernacle among — colocated mesh", "research_metaphor_colocated_mesh"),
            n("히브리서 12:26", "한 번 더 땅을 흔들리라", "is_once_more_shake_of", "shake once more — migration wave", "research_metaphor_migration_wave"),
        ],
    ),
    row(
        "zechariah_horses",
        "스가랴 말 (Zechariah Horses)",
        "스가랴 6:5",
        "하늘 사이에 선 네 영이니라",
        "ANCHOR_ZEC_6_5",
        "말 은유는 멀티 리전 패트롤·관측 에이전트 비유이며, 주가 신호가 아님.",
        [
            n("스가랴 1:8", "밤에 보이는 환상 중에", "is_night_vision_of", "night vision — dark mode ops", "research_metaphor_dark_mode_ops"),
            n("스가랴 4:6", "말과 그 마는 자로 말미암지 아니하고", "is_not_by_might_of", "not by might — not brute force", "research_metaphor_not_brute_force"),
            n("계시록 6:2", "흰 말을 탄 자가", "is_white_horse_of", "white horse — canary release", "research_metaphor_canary_release"),
            n("욥기 39:19", "말에게 능력을 주시겠느냐", "is_horse_strength_of", "horse strength — burst capacity", "research_metaphor_burst_capacity"),
        ],
    ),
    row(
        "john_baptist",
        "세례 요한 (John Baptist)",
        "마태복음 3:3",
        "광야에서 외치는 자의 소리",
        "ANCHOR_MAT_3_3",
        "요한 은유는 사전 헬스체크·스테이징 게이트 비유이며, 예언이 아님.",
        [
            n("마태복음 3:11", "나는 물로 너희에게 세례를", "is_baptize_water_of", "water baptize — smoke test", "research_metaphor_smoke_test"),
            n("요한복음 1:29", "보라 세상 죄를 지고 가는", "is_behold_lamb_of", "behold lamb — prod candidate", "research_metaphor_prod_candidate"),
            n("마가복음 1:4", "죄 사함의 세례를 전파하며", "is_preached_baptism_of", "preach baptism — preflight lint", "research_metaphor_preflight_lint"),
            n("누가복음 1:17", "엘리야의 심령과 능력으로", "is_spirit_elijah_of", "Elijah spirit — legacy monitor", "research_metaphor_legacy_monitor"),
        ],
    ),
    row(
        "magi_star",
        "동방 박사 별 (Magi Star)",
        "마태복음 2:2",
        "그의 태어나신 곳에 가서",
        "ANCHOR_MAT_2_2",
        "박사 별 은유는 외부 옵저버·트래픽 유입 비유이며, 천문 예측이 아님.",
        [
            n("마태복음 2:10", "별을 보고 크게 기뻐하고", "is_rejoiced_star_of", "rejoiced — metric spike joy", "research_metaphor_metric_spike_joy"),
            n("민수기 24:17", "한 별이 야곱에게서", "is_star_jacob_of", "star Jacob — north star KPI", "research_metaphor_north_star_kpi"),
            n("요한계시록 22:16", "다윗의 뿌리요 자손인", "is_root_offspring_of", "root offspring — lineage trace", "research_metaphor_lineage_trace"),
            n("베드로후서 1:19", "밝은 날이 흐도고", "is_day_dawns_of", "day dawns — rollout window", "research_metaphor_rollout_window"),
        ],
    ),
    row(
        "flight_egypt",
        "애굽 피신 (Flight to Egypt)",
        "마태복음 2:13",
        "아기와 그의 어머니를 데리고 애굽으로",
        "ANCHOR_MAT_2_13",
        "애굽 피신 은유는 DR 리전 페일오버·비상 이전 비유이며, 지정학이 아님.",
        [
            n("마태복음 2:15", "애굽에서 내 아들을 불렀다 하리라", "is_out_of_egypt_of", "out of Egypt — restore from DR", "research_metaphor_restore_from_dr"),
            n("호세아 11:1", "내 아들을 애굽에서 불렀다", "is_called_son_of", "called son — DR drill cite", "research_metaphor_dr_drill_cite"),
            n("출애굽기 1:22", "남자 아이는 다 죽이라", "is_kill_males_of", "kill males — hostile policy", "research_metaphor_hostile_policy"),
            n("히브리서 11:27", "왕의 노함을 무릅쓰고", "is_forsook_egypt_of", "forsook Egypt — leave bad region", "research_metaphor_leave_bad_region"),
        ],
    ),
    row(
        "temptation_wilderness",
        "광야 시험 (Wilderness Temptation)",
        "마태복음 4:10",
        "주 너의 하나님께 경배하고",
        "ANCHOR_MAT_4_10",
        "광야 시험 은유는 레드팀·프로덕션捷徑 거부 비유이며, 윤리가 아닌 매매.",
        [
            n("마태복음 4:3", "돌이 떡이 되게 하라", "is_stones_bread_of", "stones to bread — magic shortcut", "research_metaphor_magic_shortcut"),
            n("마태복음 4:6", "네 발이 돌에 부딪히지 않게", "is_pinnacle_temple_of", "pinnacle — prod from edge", "research_metaphor_prod_from_edge"),
            n("누가복음 4:13", "모든 시험을 다한 후에", "is_temptation_ended_of", "ended — pen test complete", "research_metaphor_pen_test_complete"),
            n("야고보서 1:12", "시험을 참은 자는", "is_endures_temptation_of", "endures — chaos passed", "research_metaphor_chaos_passed"),
        ],
    ),
    row(
        "rich_fool",
        "어리석은 부자 (Rich Fool)",
        "누가복음 12:20",
        "어리석은 자여 오늘 밤에",
        "ANCHOR_LUK_12_20",
        "어리석은 부자 은유는 과잉 프로비저닝·용량 낭비 비유이며, 수익 예측이 아님.",
        [
            n("누가복음 12:18", "내 곡간을 헐고 더 크게 하고", "is_build_bigger_barns_of", "bigger barns — overprovision disk", "research_metaphor_overprovision_disk"),
            n("누가복음 12:19", "여러 해 쓸 물건을 쌓아 두리라", "is_many_years_goods_of", "hoard years — unused reserve", "research_metaphor_unused_reserve"),
            n("전도서 5:13", "재물을 자기에게 해롭게 쓰는", "is_hurt_by_wealth_of", "hurt by wealth — cost overrun", "research_metaphor_cost_overrun"),
            n("잠언 11:28", "자기 재물을 의지하는 자는", "is_trusts_riches_of", "trust riches — single dependency", "research_metaphor_single_dependency"),
        ],
    ),
    row(
        "lazarus_rich",
        "나사로 부자 (Lazarus Rich Man)",
        "누가복음 16:25",
        "생전에 좋은 것을 받고",
        "ANCHOR_LUK_16_25",
        "나사로 은유는 SLO 불균형·테넌트 격차 비유이며, 내세 단정이 아님.",
        [
            n("누가복음 16:20", "가난한 자 나사로가", "is_poor_lazarus_of", "poor tenant — underprovisioned", "research_metaphor_underprovisioned"),
            n("누가복음 16:24", "이 불꽃 가운데서", "is_flame_torment_of", "flame — hot shard overload", "research_metaphor_hot_shard_overload"),
            n("누가복음 16:31", "모세와 선지자들을 듣지 아니하면", "is_not_persuaded_of", "not persuaded — ignore runbook", "research_metaphor_ignore_runbook"),
            n("야고보서 2:5", "가난한 자를 택하사", "is_chose_poor_of", "chose poor — edge tenant uplift", "research_metaphor_edge_tenant_uplift"),
        ],
    ),
    row(
        "workers_vineyard",
        "포도원 품꾼 (Workers Vineyard)",
        "마태복음 20:16",
        "나중 된 자로 먼저 되고",
        "ANCHOR_MAT_20_16",
        "포도원 은유는 지각 입사·공정성 논쟁 비유이며, 임금 예측이 아님.",
        [
            n("마태복음 20:1", "포도원에 품꾼을 들어", "is_hired_laborers_of", "hired laborers — on-demand pool", "research_metaphor_ondemand_pool"),
            n("마태복음 20:12", "우리가 종일 땀을 흘리고", "is_bore_heat_of", "bore heat — long shift SRE", "research_metaphor_long_shift_sre"),
            n("마태복음 20:15", "내 것을 가지고 내 뜻대로", "is_my_money_will_of", "my money — owner prerogative", "research_metaphor_owner_prerogative"),
            n("고린도전서 3:9", "하나님의 동역자들이니", "is_god_fellow_workers_of", "fellow workers — shared on-call", "research_metaphor_shared_oncall"),
        ],
    ),
    row(
        "wicked_tenants",
        "악한 농부 (Wicked Tenants)",
        "마태복음 21:41",
        "그 포도원을 다른 농부에게",
        "ANCHOR_MAT_21_41",
        "악한 농부 은유는 테넌트 해지·권한 회수 비유이며, 시장 청산이 아님.",
        [
            n("마태복음 21:33", "포도원을 농부에게 세로", "is_leased_vineyard_of", "leased — delegated ops", "research_metaphor_delegated_ops"),
            n("마태복음 21:38", "이는 기업자로다 죽이자", "is_kill_heir_of", "kill heir — revoke successor", "research_metaphor_revoke_successor"),
            n("누가복음 20:14", "네 것을 가지고 가라", "is_take_what_yours_of", "take yours — offboard tenant", "research_metaphor_offboard_tenant"),
            n("이사야 5:7", "포도원은 여호와의 기뻐하시는", "is_vineyard_beloved_of", "beloved vineyard — prod estate", "research_metaphor_prod_estate"),
        ],
    ),
    row(
        "olivet_discourse",
        "감람산 강해 (Olivet Discourse)",
        "마태복음 24:42",
        "그 날과 그 때를 아무도 모르니",
        "ANCHOR_MAT_24_42",
        "감람산 은유는 장애 예고·불확실성 예산 비유이며, 종말 타이밍이 아님.",
        [
            n("마태복음 24:6", "난리와 난리 소문을 들을찌니", "is_wars_rumors_of", "rumors wars — status noise", "research_metaphor_status_noise"),
            n("마태복음 24:13", "끝까지 견디는 자는", "is_endure_to_end_of", "endure — sustained SLO", "research_metaphor_sustained_slo"),
            n("마가복음 13:32", "그 날과 그 때는", "is_not_know_day_of", "unknown day — no ETA", "research_metaphor_no_eta"),
            n("데살로니가전서 5:2", "밤에 도둑이 오는 것 같이", "is_thief_night_of", "thief night — unplanned outage", "research_metaphor_unplanned_outage"),
        ],
    ),
    row(
        "betrayal_kiss",
        "가룟 키스 (Betrayal Kiss)",
        "마태복음 26:49",
        "친애하는 선생님이여 하고",
        "ANCHOR_MAT_26_49",
        "키스 배신 은유는 내부자 토큰·신뢰 위장 비유이며, 가격 신호가 아님.",
        [
            n("마태복음 26:15", "은 삼십을 주고", "is_thirty_silver_of", "thirty silver — cheap bribe", "research_metaphor_cheap_bribe"),
            n("마태복음 26:50", "친구여 네가 한 일을 하라", "is_do_quickly_of", "do quickly — fast exfil", "research_metaphor_fast_exfil"),
            n("시편 41:9", "내 떡을 먹던 자가", "is_ate_bread_of", "ate bread — insider access", "research_metaphor_insider_access"),
            n("요한복음 13:27", "사탄이 그에게 들어가니", "is_satan_entered_of", "entered — compromised session", "research_metaphor_compromised_session"),
        ],
    ),
    row(
        "ananias_sapphira",
        "아나니아 삽비라 (Ananias Sapphira)",
        "사도행전 5:5",
        "아나니아가 이 말을 듣고 쓰러져 죽으니",
        "ANCHOR_ACT_5_5",
        "아나니아 은유는 메트릭 허위 보고·감사 실패 비유이며, 형벌이 아님.",
        [
            n("사도행전 5:2", "그의 아내가 알더라", "is_wife_knew_of", "wife knew — shared fraud", "research_metaphor_shared_fraud"),
            n("사도행전 5:9", "어찌하여 사탄이 네 마음에", "is_test_spirit_of", "test spirit — integrity probe", "research_metaphor_integrity_probe"),
            n("잠언 11:1", "속이는 저울은 여호와께 미움을", "is_dishonest_scales_of", "dishonest scales — fake metrics", "research_metaphor_fake_metrics"),
            n("갈라디아서 6:7", "무엇을 심든지 그대로 거두리라", "is_reap_sow_of", "reap sow — audit consequence", "research_metaphor_audit_consequence"),
        ],
    ),
    row(
        "lydda_aeneas",
        "루다 에네아 (Lydda Aeneas)",
        "사도행전 9:34",
        "에네아야 일어나 네 자리를 정돈하라",
        "ANCHOR_ACT_9_34",
        "에네아 은유는 단일 노드 복구·핫픽스 비유이며, 의료가 아님.",
        [
            n("사도행전 9:35", "루다와 사례에 사는 모든 사람에게", "is_lydda_sharon_of", "region heal — zone recovery", "research_metaphor_zone_recovery"),
            n("요한복음 5:8", "일어나 네 자리를 들라", "is_take_up_bed_of", "take bed — restore pod", "research_metaphor_restore_pod"),
            n("히브리서 12:12", "누운 손과 약한 무릎을", "is_strengthen_limbs_of", "strengthen — patch weak link", "research_metaphor_patch_weak_link"),
            n("이사야 35:6", "절름발이가 사슴 같이", "is_lame_leap_of", "lame leap — latency fixed", "research_metaphor_latency_fixed"),
        ],
    ),
    row(
        "mars_hill",
        "아레오파고 (Mars Hill)",
        "사도행전 17:23",
        "알지 못하는 신에게라",
        "ANCHOR_ACT_17_23",
        "아레오파고 은유는 미지 요구·그린필드 피치 비유이며, 투자 유치가 아님.",
        [
            n("사도행전 17:21", "새로운 것을 말하거나 듣기를", "is_tell_hear_new_of", "new things — novelty chasing", "research_metaphor_novelty_chasing"),
            n("사도행전 17:32", "사람이 다룻다가 말을 듣고", "is_some_mocked_of", "some mocked — mixed review", "research_metaphor_mixed_review"),
            n("고린도전서 1:23", "십자가는 유대인에게는 거리끼는", "is_cross_foolish_of", "foolish cross — unpopular design", "research_metaphor_unpopular_design"),
            n("로마서 1:20", "보이는 것들로 알 수 있나니", "is_seen_understood_of", "seen understood — observable metrics", "research_metaphor_observable_metrics"),
        ],
    ),
    row(
        "onesimus_letter",
        "오네시모 편지 (Onesimus Letter)",
        "빌레몬 1:16",
        "더불어 영원히 존재할 형제로",
        "ANCHOR_PHM_1_16",
        "오네시모 은유는 탈주 워커·관계 복구 비유이며, HR이 아님.",
        [
            n("빌레몬 1:10", "내 아들 오네시모를 위하여", "is_son_onesimus_of", "son Onesimus — renamed asset", "research_metaphor_renamed_asset"),
            n("빌레몬 1:18", "만일 아무 해를 끼쳤거나", "is_owes_charge_of", "owes charge — tech debt note", "research_metaphor_tech_debt_note"),
            n("골로새서 4:9", "충성되고 사랑하는 형제요", "is_faithful_beloved_of", "faithful — reliable worker", "research_metaphor_reliable_worker"),
            n("골로새서 3:25", "주께 하는 것 같이 사람에게", "is_as_to_lord_of", "as to Lord — owner mindset", "research_metaphor_owner_mindset"),
        ],
    ),
    row(
        "love_chapter",
        "사랑 장 (Love Chapter)",
        "고린도전서 13:8",
        "사랑은 언제까지나 떨어지지 아니하나",
        "ANCHOR_1CO_13_8",
        "사랑 장 은유는 팀 코어 가치·장기 유지보수 비유이며, 감정 예측이 아님.",
        [
            n("고린도전서 13:1", "방언을 사람과 천사의 말로 하여도", "is_speaks_tongues_of", "tongues without love — noisy logs", "research_metaphor_noisy_logs"),
            n("고린도전서 13:2", "모든 신앙으로 산을 옮길 수 있어도", "is_faith_move_mountains_of", "faith mountains — power without care", "research_metaphor_power_without_care"),
            n("고린도전서 13:13", "믿음, 소망, 사랑, 이 세 가지는", "is_faith_hope_love_of", "three remain — core values", "research_metaphor_core_values"),
            n("요한일서 4:8", "하나님은 사랑이시라", "is_god_is_love_of", "God is love — culture north star", "research_metaphor_culture_north_star"),
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
