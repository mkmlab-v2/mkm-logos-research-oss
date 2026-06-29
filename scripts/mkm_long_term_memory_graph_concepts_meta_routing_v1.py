"""Meta-routing LTM concepts — 12AI · 4AI · lane resume ([HYPO] / B-track)."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

META_ROUTING_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="twelve_ai_routing_contract",
        label_ko="12AI routing · S/K/L/M (+E B-track)",
        essence=(
            "Cursor 역할 분업 Router/Architect/Librarian/Sentinel — 모델 12개·코드북 1:1 아님 · parallel cap 4"
        ),
        must_keep_tags=("Parallel cap", "Architect", "Librarian", "Sentinel"),
        query_aliases=(
            "12ai",
            "12 ai",
            "routing",
            "router",
            "librarian",
            "architect",
            "sentinel",
            "mutator",
            "orchestration",
        ),
        field_tags=("meta_routing", "cursor", "12ai", "governance"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path=".cursor/skills/auto-12ai-routing/SKILL.md",
                anchor_start="## Routing defaults",
                anchor_end="## Fact-Lock",
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path=".cursor/rules/12ai-orchestration.mdc",
                anchor_start="## 1) 역할 편제",
                anchor_end="## 2) 요청 라우팅",
            ),
        ),
        related_concepts=("mkm_orchestrator_todo_queue", "ltm_graph_self_meta", "lane_resume_pack_contract"),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="four_ai_lens_output_contract",
        label_ko="4AI lens output · Field→Lens→Final",
        essence="사상/명리/성경(Logos) 3렌즈 · Macro/Regime는 렌즈명 아님 · 실전 트리거=regime_map+ops gate",
        must_keep_tags=("사상", "명리", "성경(Logos)", "regime_map"),
        query_aliases=(
            "4ai",
            "4 ai",
            "lens",
            "렌즈",
            "field lens conflict",
            "multi-lens",
            "logos",
            "myeongni",
            "sasang lens",
        ),
        field_tags=("meta_routing", "lens", "4ai", "oracle"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="AGENTS.md",
                anchor_start="## Fact-Lock · 격벽",
                anchor_end="## 재개 · 종료",
            ),
        ),
        related_concepts=(
            "regime_field_primary_map",
            "lens_logos_non_gating_pack",
            "absolute_balance_coordinator_mode",
        ),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="absolute_balance_coordinator_mode",
        label_ko="Absolute Balance · coordinator state (not 5th AI)",
        essence="MKM=4AI core+Absolute Balance Coordinator Mode · 제5 AI/체질 표기 금지",
        must_keep_tags=("4AI core", "Coordinator Mode", "제5 AI"),
        query_aliases=(
            "absolute balance",
            "coordinator mode",
            "4ai core",
            "태양",
            "소양",
            "태음",
            "소음",
        ),
        field_tags=("meta_routing", "4ai", "naming", "oracle"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="AGENTS.md",
                anchor_start="## Fact-Lock · 격벽",
                anchor_end="## 재개 · 종료",
            ),
        ),
        related_concepts=("four_ai_lens_output_contract",),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="lane_resume_pack_contract",
        label_ko="Lane resume pack · context diet inject",
        essence="build_mkm_chat_resume_pack_v1.py --lane ms|oracle|infra|design · MISSION_LOG 전체 붙이지 않음",
        must_keep_tags=("--lane", "LANE_OPS_PACKS"),
        query_aliases=(
            "resume pack",
            "chat resume",
            "lane pack",
            "context diet",
            "ms lane",
            "oracle lane",
            "infra lane",
            "design lane",
        ),
        field_tags=("meta_routing", "resume", "ltm", "cursor"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/build_mkm_chat_resume_pack_v1.py",
                anchor_start='        "--lane",',
                anchor_end="    args = ap.parse_args",
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md",
                anchor_start="**Machine inject:**",
                anchor_end="## Session start",
            ),
        ),
        related_concepts=("central_resume_protocol", "twelve_ai_routing_contract", "ltm_graph_self_meta"),
    ),
)
