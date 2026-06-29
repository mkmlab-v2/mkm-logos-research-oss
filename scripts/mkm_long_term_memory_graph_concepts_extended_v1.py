"""Extended LTM graph concepts — MS / Infra / Design / compression / lenses ([HYPO])."""

from __future__ import annotations



from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec



EXTENDED_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (

    ConceptSpec(

        concept_id="compression_track_a_active_kpi",

        label_ko="Track A active KPI · 47.5% / ~0.890",

        essence=(

            "MULTILENS active report SSOT — global saving ~47.1% · Jaccard ~0.890; "

            "human sign-off only; repair≠core"

        ),

        must_keep_tags=("global_token_saving_rate", "avg_reconstruction_fidelity_jaccard"),

        query_aliases=(

            "track a",

            "47.5",

            "0.890",

            "jaccard",

            "compression kpi",

            "multilens",

            "active report",

            "압축",

        ),

        field_tags=("compression", "track_a", "ms", "fact_lock"),

        priority=9,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",

                json_pointers=(

                    "/compression_metrics/global_token_saving_rate",

                    "/compression_metrics/avg_reconstruction_fidelity_jaccard",

                ),

            ),

        ),

        related_concepts=("compression_fail_comp004_boundary", "send_gate_hold_doctrine", "ms_lane_submission_hold"),

        lane_hint="ms",

    ),

    ConceptSpec(

        concept_id="compression_fail_comp004_boundary",

        label_ko="FAIL-COMP-004 · 벤치↔상용 격벽",

        essence="압축 벤치·연구와 Track A·실매매·시그널 자동 합선 금지 — SLA policy",

        must_keep_tags=("FAIL-COMP-004", "Track A"),

        query_aliases=("fail-comp", "fail comp", "004", "sla", "literal", "ultra-literal", "합선"),

        field_tags=("compression", "fact_lock", "track_a", "btrack"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/final/COMPRESSION_SLA_POLICY_V1.md",

                anchor_start="### Operating summary",

                anchor_end="## 1. Purpose",

            ),

        ),

        related_concepts=("compression_track_a_active_kpi",),

        lane_hint="ms",

    ),

    ConceptSpec(

        concept_id="ms_lane_submission_hold",

        label_ko="MS 제출 HOLD · apply_forbidden",

        essence="MS 47.5%/0.890 제출본 vs 내부 policy; NG apply_forbidden; 포털 재제출 금지",

        must_keep_tags=("금지", "47%", "counsel"),

        query_aliases=("ms", "제출", "국방", "defense", "hwp", "ng", "340"),

        field_tags=("ms", "compression", "send_gate", "governance"),

        priority=9,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="MISSION_LOG.md",

                anchor_start="| **MS·B2B 압축** |",

                anchor_end="| **Infra·solo** |",

            ),

        ),

        related_concepts=("send_gate_hold_doctrine", "compression_track_a_active_kpi"),

        lane_hint="ms",

    ),

    ConceptSpec(

        concept_id="infra_solo_scheduler_stack",

        label_ko="Solo scheduler core stack · tier0–3",

        essence="1인 solo 스케줄러 SSOT — tier0 daily·weekly; unauthorized_ready=0; Track A 승격 없음",

        must_keep_tags=("mkm_scheduler_solo_core_stack_v1", "tier0_core_daily"),

        query_aliases=("scheduler", "solo stack", "tier0", "schtasks", "예약", "solo_ops"),

        field_tags=("infra", "scheduler", "solo", "governance"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json",

                json_pointers=("/schema", "/tier0_core_daily"),

            ),

        ),

        related_concepts=("infra_parallel_passive_loop",),

        lane_hint="infra",

    ),

    ConceptSpec(

        concept_id="infra_parallel_passive_loop",

        label_ko="병렬 패시브 루프 · 3레인",

        essence="shim·L1 canary·MAX_HYPO 병렬 패시브 — research_only; Nebius D레인 STOP",

        must_keep_tags=("parallel_passive_loop_v1", "research_only", "track_a_active_write"),

        query_aliases=("parallel passive", "병렬 패시브", "passive loop", "shim", "canary", "max_hypo"),

        field_tags=("infra", "btrack", "oracle", "passive"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="reports/parallel_passive_loop_v1_latest.json",

                json_pointers=("/schema", "/research_only", "/track_a_active_write"),

            ),

        ),

        related_concepts=("infra_solo_scheduler_stack", "web_ops_regime_gate_nebius"),

        lane_hint="infra",

    ),

    ConceptSpec(

        concept_id="design_showroom_domain_portfolio",

        label_ko="Design/Showroom · 도메인 포트폴리오",

        essence="jemaai.cloud 쇼룸·허브 — 실매매 격리; domain portfolio SSOT; hub smoke",

        must_keep_tags=("jemaai.cloud", "실매매", "SSOT"),

        query_aliases=("design", "showroom", "jemaai", "hub", "쇼룸", "허브", "portfolio"),

        field_tags=("design", "showroom", "track_c", "web"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",

                anchor_start="## 1) 도메인",

                anchor_end="### 1.1 쇼룸",

            ),

        ),

        related_concepts=("send_gate_hold_doctrine",),

        lane_hint="design",

    ),

    ConceptSpec(

        concept_id="lens_myeongni_notebooklm_pack",

        label_ko="NotebookLM LENS_MYEONGNI · 결정론 §3.3",

        essence="명리 NL pack — CONSTITUTION §3.3; 개인 실명 업로드 금지; Track A 자동 합선 금지",

        must_keep_tags=("LENS_MYEONGNI", "HYPO"),

        query_aliases=("myeongni", "명리", "manseryeok", "만세력", "lens_myeongni"),

        field_tags=("myeongni", "lens", "notebooklm", "hypos"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/NotebookLM_sources_manifest.md",

                anchor_start="| **명리 Myeongni (B)** |",

                anchor_end="| **성경 Logos",

            ),

        ),

        related_concepts=("myeongni_pack0b_training_observation",),

        lane_hint="oracle",

    ),

    ConceptSpec(

        concept_id="lens_logos_non_gating_pack",

        label_ko="NotebookLM LENS_LOGOS · NON_GATING",

        essence="성경 Logos NL pack — 거시 해설·NON_GATING; 실전 트리거 금지",

        must_keep_tags=("LENS_LOGOS", "NON_GATING"),

        query_aliases=("logos", "성경", "non_gating", "non-gating", "lens_logos"),

        field_tags=("logos", "lens", "notebooklm", "non_gating"),

        priority=7,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/NotebookLM_sources_manifest.md",

                anchor_start="| **성경 Logos (B, NON_GATING)** |",

                anchor_end="| **Track C / 사업** |",

            ),

        ),

        related_concepts=("prophecy_research_only_boundary",),

        lane_hint="oracle",

    ),

    ConceptSpec(

        concept_id="regime_field_primary_map",

        label_ko="레짐 Field · regime_map 1차 주",

        essence="1차 실물 regime_map 주 · 2차 성경/명리 보 — 2차는 실전 트리거 금지",

        must_keep_tags=("regime_map", "실전 트리거"),

        query_aliases=("regime", "레짐", "field", "imf", "lehman", "regime_map"),

        field_tags=("regime", "field", "governance", "fact_lock"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/final/CENTRAL_AGENT_MEMORY_V1.md",

                anchor_start="| 레짐 주·보 |",

                anchor_end="| Multi-Lens",

            ),

        ),

        related_concepts=("fact_lock_implementation",),

    ),

    ConceptSpec(

        concept_id="local_vps_one_rule_workflow",

        label_ko="로컬↔VPS 한 원칙 · 코드 sync vs live ON",

        essence="코드/전략 동기화는 상시 · 실전 주문 ON은 별도 승인 게이트",

        must_keep_tags=("실전 주문", "동기화", "SSOT"),

        query_aliases=("vps", "local", "pm2", "ssh", "배포", "git pull", "live trading"),

        field_tags=("infra", "vps", "governance", "fact_lock"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md",

                anchor_start="## 표준 결론",

                anchor_end="## 역할 표",

            ),

        ),

        related_concepts=(
            "send_gate_hold_doctrine",
            "trading_go_nogo_status_ssot",
            "vps_pm2_live_entry_boundary",
        ),

        lane_hint="infra",

    ),

    ConceptSpec(

        concept_id="notebooklm_mcp_auth_bridge",

        label_ko="NotebookLM MCP · get_health ≠ UI 로그인",

        essence="Vault≠cloud≠MCP 3채널; MCP 전용 Chrome; setup_auth/re_auth",

        must_keep_tags=("get_health", "setup_auth"),

        query_aliases=("notebooklm mcp", "mcp auth", "nl mcp", "authenticated", "vault"),

        field_tags=("notebooklm", "mcp", "infra", "nl"),

        priority=7,

        coordinates=(

            CoordinateSpec(

                kind="markdown_anchor",

                file_path="docs/NotebookLM_sources_manifest.md",

                anchor_start="### MCP `notebooklm-mcp` 인증",

                anchor_end="#### 노트북당 소스 한도",

            ),

        ),

        related_concepts=("lens_sasang_notebooklm_pack",),

        lane_hint="infra",

    ),

    ConceptSpec(

        concept_id="news_neutralizer_shadow_weekly",

        label_ko="News neutralizer shadow · weekly",

        essence="RSS bias cluster shadow — research_only; auto_deck_publish false",

        must_keep_tags=("research_only", "hypothesis_tag", "promotion_required"),

        query_aliases=("news neutralizer", "neutralizer", "rss", "bias", "뉴스"),

        field_tags=("infra", "news", "btrack", "hypos"),

        priority=7,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="reports/news_neutralizer_shadow_v1_latest.json",

                json_pointers=("/lane", "/hypothesis_tag", "/promotion_required"),

            ),

        ),

        related_concepts=("prophecy_research_only_boundary",),

        lane_hint="infra",

    ),

    ConceptSpec(

        concept_id="web_ops_regime_gate_nebius",

        label_ko="Web ops regime gate · Nebius no-GPU",

        essence="web_ops_regime_gate — no_gpu_spinup; prepaid; Tier3 human only",

        must_keep_tags=("no_gpu_spinup", "research_only", "nebius_prepaid_only"),

        query_aliases=("web_ops", "nebius", "regime gate", "gpu spinup", "tier3", "cost"),

        field_tags=("web_ops", "infra", "nebius", "regime"),

        priority=8,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="reports/web_ops_regime_gate_v1_latest.json",

                json_pointers=("/research_only", "/cost_policy/no_gpu_spinup", "/cost_policy/nebius_prepaid_only"),

            ),

        ),

        related_concepts=("infra_parallel_passive_loop",),

        lane_hint="web_ops",

    ),

    ConceptSpec(

        concept_id="compression_moat_open_bench",

        label_ko="Moat open-bench · contributor_provided",

        essence="GitHub contributor bench — pass_rate gate; SEND_GATE HOLD; customer_provided false",

        must_keep_tags=("HOLD", "contributor_provided"),

        query_aliases=("moat", "open bench", "contributor", "github pr", "community"),

        field_tags=("compression", "btrack", "ms", "moat"),

        priority=7,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json",

                json_pointers=(

                    "/send_gate",

                    "/labels",

                    "/purpose_ko",

                ),

            ),

        ),

        related_concepts=("compression_fail_comp004_boundary", "send_gate_hold_doctrine"),

        lane_hint="ms",

    ),

    ConceptSpec(

        concept_id="myeongni_pack0b_training_observation",

        label_ko="명리 Pack0B train · locked_eval 관측",

        essence="Pack0B ~233/500 train — parse/align baseline; SEND_GATE HOLD; KOSPI role 합선 금지",

        must_keep_tags=("research_only", "[HYPO]", "Pack 0-B"),

        query_aliases=("pack0b", "pack 0", "lora", "locked_eval", "명리 train"),

        field_tags=("myeongni", "oracle", "infra", "training"),

        priority=7,

        coordinates=(

            CoordinateSpec(

                kind="json_pointer",

                file_path="reports/myeongri_pack0b_pillars_emphasis_experiment_spec_v1_latest.json",

                json_pointers=(

                    "/research_only",

                    "/hypothesis_tag",

                    "/title",

                ),

            ),

        ),

        related_concepts=("lens_myeongni_notebooklm_pack",),

        lane_hint="oracle",

    ),

    ConceptSpec(

        concept_id="ltm_graph_self_meta",

        label_ko="LTM graph self · rebuild chain",

        essence="storage/meta/mkm_long_term_memory_graph_v1.json — graph→doctrine overlay→resume",

        must_keep_tags=("mkm_long_term_memory_graph_v1", "research_only"),

        query_aliases=(
            "ltm graph",
            "long term memory",
            "doctrine overlay",
            "ops memory graph",
            "self meta",
            "ltm graph os",
            "concept count",
            "topology",
        ),

        field_tags=("ltm", "memory", "graph", "resume", "meta", "infra"),

        priority=6,

        coordinates=(

            CoordinateSpec(

                kind="file_excerpt",

                file_path="scripts/build_mkm_long_term_memory_graph_v1.py",

                anchor_start='"""Build storage/meta/mkm_long_term_memory_graph_v1.json',

                anchor_end="if __name__",

            ),

        ),

        related_concepts=("central_resume_protocol", "fact_lock_implementation"),

        lane_hint="infra",

    ),

)

