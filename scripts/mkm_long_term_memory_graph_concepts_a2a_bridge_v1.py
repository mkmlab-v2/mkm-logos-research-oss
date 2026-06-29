"""LTM ↔ Inter-Agent A2A bridge concepts ([HYPO] / B-track · RQ-019)."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

A2A_BRIDGE_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="a2a_two_layer_architecture_ssot",
        label_ko="A2A 2-layer · ops memory vs inter-agent wire",
        essence=(
            "Physical/ops_memory/inter_agent_rq019/btrack layers — "
            "mkm_a2a_two_layer_architecture_v1 · canvas cross-ref"
        ),
        must_keep_tags=("mkm_a2a_two_layer_architecture_v1", "research_only"),
        query_aliases=("a2a", "two layer", "ops memory", "inter agent", "rq-019", "rq019"),
        field_tags=("meta_routing", "a2a", "ops_memory", "research"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/mkm_a2a_two_layer_architecture_v1_latest.json",
                json_pointers=("/schema", "/research_only", "/layers", "/theory_placement"),
            ),
        ),
        related_concepts=(
            "ltm_ops_inject_to_a2a_wire",
            "inter_agent_encoding_smoke_chain",
            "a2a_ltm_track_wall",
        ),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="ltm_ops_inject_to_a2a_wire",
        label_ko="LTM ltm_* overlay → ops inject → A2A tp01 pilot",
        essence=(
            "build_ltm_a2a_bridge_map_v1 maps ltm_* nodes to wire profile · "
            "tp01 resume compress pilot — human MD unchanged"
        ),
        must_keep_tags=("mkm_chat_resume_a2a_pilot_v1", "tp01"),
        query_aliases=(
            "ltm overlay",
            "ops inject",
            "a2a pilot",
            "tp01",
            "wire handoff",
            "bridge map",
        ),
        field_tags=("meta_routing", "a2a", "ltm", "ops_memory"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
                anchor_start='"""tp01 A2A pilot',
                anchor_end="boundary_ack",
            ),
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/MKM_OPS_MEMORY_AI_TO_AI_DEV_ONE_PAGER_V1.md",
                anchor_start="## Design (3 layers)",
                anchor_end="## NODE_SPECS",
            ),
        ),
        related_concepts=("a2a_two_layer_architecture_ssot", "lane_resume_pack_contract"),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="inter_agent_encoding_smoke_chain",
        label_ko="Inter-Agent encoding smoke · RQ-019",
        essence=(
            "Invoke-MkmInterAgentEncodingSmoke_v1 → pytest bundle + "
            "build_mkm_inter_agent_encoding_status_v1 · wire_profile_v0"
        ),
        must_keep_tags=("build_mkm_inter_agent_encoding_status_v1", "Inter-agent encoding pytest"),
        query_aliases=(
            "encoding smoke",
            "inter agent encoding",
            "wire profile",
            "compression v2 stub",
            "dialogue mock",
        ),
        field_tags=("fuel", "a2a", "compression", "research"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/Invoke-MkmInterAgentEncodingSmoke_v1.ps1",
                anchor_start="== Inter-agent encoding pytest ==",
                anchor_end="SkipWorkedExampleEmit",
            ),
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
                json_pointers=("/schema", "/layers/packet", "/operations"),
            ),
        ),
        related_concepts=("a2a_two_layer_architecture_ssot", "a2a_ltm_track_wall"),
        lane_hint="infra",
    ),
    ConceptSpec(
        concept_id="a2a_ltm_track_wall",
        label_ko="A2A·LTM track wall · no Track A·live merge",
        essence=(
            "ltm_a2a_bridge_wall_v1 forbidden_auto_merge — "
            "SEND_GATE HOLD · MS headline·oper SSOT read-only"
        ),
        must_keep_tags=("forbidden_auto_merge", "live_trading_enable"),
        query_aliases=("track wall", "no track a", "no live merge", "a2a wall", "forbidden"),
        field_tags=("packaging", "a2a", "governance", "fact_lock"),
        priority=9,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/ltm_a2a_bridge_wall_v1.json",
                json_pointers=("/forbidden_auto_merge", "/allowed_uses", "/boundary_ack"),
            ),
        ),
        related_concepts=(
            "send_gate_hold_doctrine",
            "a2a_two_layer_architecture_ssot",
            "compression_track_a_active_kpi",
        ),
        lane_hint="infra",
    ),
)
