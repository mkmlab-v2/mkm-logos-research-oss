"""Research-layer LTM graph concepts — NL sandbox · ingest gate ([HYPO] / B-track)."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

RESEARCH_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="nl_research_sandbox_tier_b_gate",
        label_ko="NL_RESEARCH_SANDBOX · Tier B ingest gate",
        essence=(
            "external_source_review · sandbox_only · Tier A Core 5 auto 이관 금지 · "
            "run_ltm_research_sandbox_cycle_v1 human sign-off before graph append"
        ),
        must_keep_tags=("NL_RESEARCH_SANDBOX", "external_source_review", "research_only"),
        query_aliases=(
            "nl research sandbox",
            "notebooklm sandbox",
            "tier b",
            "ingest gate",
            "external source review",
            "research seed",
        ),
        field_tags=("research", "notebooklm", "ingest", "sandbox"),
        priority=6,
        coordinates=(
            CoordinateSpec(
                kind="markdown_anchor",
                file_path="docs/final/templates/notebooklm_research_seed_sandbox_tier_b_v1.template.md",
                anchor_start="**target_notebook:**",
                anchor_end="## 메타",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="docs/final/artifacts/ltm_research_sandbox_cycle_contract_v1.json",
                anchor_start='"ingest_gate": "external_source_review"',
                anchor_end='"kill_matrix"',
            ),
        ),
        related_concepts=("ltm_graph_self_meta", "fact_lock_implementation"),
        lane_hint="oracle",
    ),
)
