"""Trading live guard LTM subgraph — LOCAL_VS_VPS · GO/NO_GO · human approval ([HYPO])."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

TRADING_GUARD_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="trading_go_nogo_status_ssot",
        label_ko="Trading GO/NO_GO · 단일 verdict SSOT",
        essence=(
            "build_trading_go_nogo_status_v1 → trading_go_no_go_latest.json · "
            "conditional_gate + human approval + Fact-Safe risk 합성 · 주문 없음"
        ),
        must_keep_tags=("trading_go_no_go", "build_trading_go_nogo_status_v1"),
        query_aliases=(
            "go no go",
            "go_nogo",
            "trading verdict",
            "live trading gate",
            "conditional_gate",
        ),
        field_tags=("packaging", "trading", "governance", "fact_lock", "infra"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                anchor_start="| 트레이딩 단일 판정 파일",
                anchor_end="| Fact-Safe 리스크",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/build_trading_go_nogo_status_v1.py",
                anchor_start='"""Build single-file trading GO/NO_GO',
                anchor_end="DEFAULT_OUT =",
            ),
        ),
        related_concepts=(
            "trading_human_execution_approval_gate",
            "fact_safe_risk_sync_chain",
            "local_vps_one_rule_workflow",
            "athena_ecc_execution_governance",
        ),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="trading_human_execution_approval_gate",
        label_ko="Human-in-the-Loop · trading execution approval",
        essence=(
            "validate_trading_human_execution_approval_v1 · "
            "reports/trading_human_execution_approval_latest.json · "
            "conditional gate exit 7 if missing/invalid"
        ),
        must_keep_tags=(
            "trading_human_execution_approval",
            "validate_trading_human_execution_approval_v1",
        ),
        query_aliases=(
            "human approval",
            "human in the loop",
            "execution approval",
            "MKM_TRADING_HUMAN_APPROVAL_JSON",
        ),
        field_tags=("packaging", "trading", "governance", "security"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                anchor_start="| 트레이딩 Human-in-the-Loop",
                anchor_end="| 에이전트 레인 분리",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/validate_trading_human_execution_approval_v1.py",
                anchor_start='"""Validate trading_human_execution_approval_v1',
                anchor_end="Exit codes:",
            ),
        ),
        related_concepts=(
            "trading_go_nogo_status_ssot",
            "athena_ecc_execution_governance",
            "send_gate_hold_doctrine",
        ),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="vps_pm2_live_entry_boundary",
        label_ko="VPS PM2 live entry · start_live_trading",
        essence=(
            "cwd=모노레포 루트 · start_live_trading.py → start_24h_daemon · "
            "코드 sync ≠ 주문 ON · pm2 show exec cwd SSOT"
        ),
        must_keep_tags=("start_live_trading", "pm2 show"),
        query_aliases=(
            "pm2",
            "start_live_trading",
            "24h daemon",
            "vps live",
            "bitcoin-live",
        ),
        field_tags=("infra", "vps", "trading", "governance"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md",
                anchor_start="## VPS 배치 (권장)",
                anchor_end="## VPS에 SSH",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="projects/bitcoin-trading/start_live_trading.py",
                anchor_start='"""',
                anchor_end="def main",
            ),
        ),
        related_concepts=(
            "local_vps_one_rule_workflow",
            "trading_go_nogo_status_ssot",
        ),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="fact_safe_risk_sync_chain",
        label_ko="Fact-Safe risk sync · conditional gate chain",
        essence=(
            "Run-FactSafeRiskProfileSyncChain → sync_fact_safe_risk_profile · "
            "run_conditional_action_gate_v1 → build_trading_go_nogo_status_v1"
        ),
        must_keep_tags=("sync_fact_safe_risk_profile", "Run-FactSafeRiskProfileSyncChain"),
        query_aliases=(
            "fact safe",
            "fact-safe",
            "risk profile sync",
            "conditional action gate",
            "Run-FactSafeRiskProfileSyncChain",
        ),
        field_tags=("fuel", "trading", "infra", "governance"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                anchor_start="| Fact-Safe 리스크 주기 갱신",
                anchor_end="| 환경 스냅샷",
            ),
        ),
        related_concepts=(
            "trading_go_nogo_status_ssot",
            "local_vps_one_rule_workflow",
        ),
        lane_hint="infra",
    ),
)
