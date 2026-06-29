"""Logos Oracle LTM graph concepts — wiring guard · sandbox dynamic tuning ([HYPO] / B-track)."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

LOGOS_ORACLE_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="logos_theory_implementation_wiring",
        label_ko="Logos theory→implementation wiring guard",
        essence=(
            "canonical_edges registry · forbidden_aliases · "
            "check_logos_theory_implementation_wiring_v1 · re-invention guard"
        ),
        must_keep_tags=("HYPO", "research_only", "logos_theory_implementation_wiring_v1"),
        query_aliases=(
            "logos wiring",
            "theory implementation wiring",
            "dynamic_override",
            "bridge_v1_dynamic_override",
            "Fusion_Schema",
            "re-invention guard",
        ),
        field_tags=("logos", "oracle", "wiring", "btrack"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="docs/final/artifacts/logos_theory_implementation_wiring_v1.json",
                anchor_start='"schema": "logos_theory_implementation_wiring_v1"',
                anchor_end='"verify_command"',
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/check_logos_theory_implementation_wiring_v1.py",
                anchor_start="def check_registry",
                anchor_end="return errors",
            ),
        ),
        related_concepts=("lens_logos_non_gating_pack", "fact_lock_implementation"),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="logos_spread_sandbox_dynamic_tuning",
        label_ko="Logos spread sandbox · dynamic tuning",
        essence=(
            "gematria_bridge_sandbox_v1 + logos_dynamic_tuning_v1 softmax/geumhwa · "
            "orb_ui_hints sidecar · must not replace production gematria_bridge_v1"
        ),
        must_keep_tags=("HYPO", "geumhwa", "gematria_bridge_v1"),
        query_aliases=(
            "dynamic tuning",
            "spread tuning",
            "geumhwa decay",
            "orb ui hints",
            "lattice mesh strength",
            "logos dynamic resonance",
        ),
        field_tags=("logos", "sandbox", "spread", "ui_wire"),
        priority=6,
        coordinates=(
            CoordinateSpec(
                kind="file_excerpt",
                file_path="scripts/core/logos_dynamic_tuning_v1.py",
                anchor_start="geumhwa decay ([HYPO])",
                anchor_end="def orb_ui_hints_from_dynamic",
            ),
            CoordinateSpec(
                kind="file_excerpt",
                file_path="docs/final/artifacts/logos_theory_implementation_wiring_v1.json",
                anchor_start='"edge_id": "spread_dynamic_tuning"',
                anchor_end='"repro_command"',
            ),
        ),
        related_concepts=(
            "logos_theory_implementation_wiring",
            "lens_logos_non_gating_pack",
        ),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="logos_cosmic_anchor_graph_math",
        label_ko="Logos cosmic anchor graph · gematria_bridge_v1",
        essence=(
            "339 lemma anchors · 200 narratives · resonance edges · "
            "logos_cosmic_anchor_graph_bridge_v1 · structural B-track only"
        ),
        must_keep_tags=("gematria_bridge_v1", "research_only", "narrative_sample_count"),
        query_aliases=(
            "cosmic anchor",
            "anchor graph",
            "lemma hit",
            "resonance edge",
            "339 anchors",
            "gematria bridge",
        ),
        field_tags=("logos", "anchor", "graph", "gematria", "btrack"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json",
                json_pointers=(
                    "/kernel_recipe_id",
                    "/summary/lemma_hit_anchors",
                    "/summary/narrative_sample_count",
                    "/research_only",
                ),
            ),
        ),
        related_concepts=(
            "logos_theory_implementation_wiring",
            "logos_gematria_dual_gate",
            "lens_logos_non_gating_pack",
        ),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="logos_router_regression_bundle",
        label_ko="Logos router regression bundle · P21",
        essence=(
            "run_logos_router_regression_bundle_v1 — bloom cap guard · gold 12/12 · "
            "narrative router_hit structural · send_gate HOLD"
        ),
        must_keep_tags=("chain_pass", "send_gate", "gold_required_all_pass"),
        query_aliases=(
            "router regression",
            "p21 bundle",
            "gold required",
            "router hit",
            "bloom cap",
            "graphrag router",
        ),
        field_tags=("logos", "router", "gold", "regression", "btrack"),
        priority=8,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/logos_router_regression_bundle_v1_latest.json",
                json_pointers=(
                    "/chain_pass",
                    "/send_gate",
                    "/bloom_cap",
                    "/gold_eval/gold_required_all_pass",
                ),
            ),
        ),
        related_concepts=(
            "logos_cosmic_anchor_graph_math",
            "logos_4d_state_non_gating",
            "a2a_ltm_track_wall",
        ),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="logos_4d_state_non_gating",
        label_ko="Logos 4D daily state · [NON_GATING]",
        essence=(
            "logos_4d_state_v1 — WATCH quadrant · narrative_oracle assist only · "
            "no production regime trigger"
        ),
        must_keep_tags=("[NON_GATING]", "regime_tag", "WATCH"),
        query_aliases=(
            "4d state",
            "vector 4d",
            "quadrant",
            "WATCH regime",
            "non gating",
            "narrative oracle",
        ),
        field_tags=("logos", "4d", "regime", "non_gating"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/logos_4d_state_v1_latest.json",
                json_pointers=(
                    "/quadrant_info/regime_tag",
                    "/narrative_oracle/policy_tag",
                    "/narrative_oracle/action",
                ),
            ),
        ),
        related_concepts=(
            "lens_logos_non_gating_pack",
            "logos_cosmic_anchor_graph_math",
            "logos_gematria_dual_gate",
        ),
        lane_hint="oracle",
    ),
    ConceptSpec(
        concept_id="logos_gematria_dual_gate",
        label_ko="Logos gematria 4D dual gate · prod vs sandbox",
        essence=(
            "logos_anchor_resonance_dual_gate — gematria_bridge_v1 production vs "
            "sandbox spread geometry · research_only"
        ),
        must_keep_tags=("gematria_bridge_v1", "research_only"),
        query_aliases=(
            "dual gate",
            "gematria gate",
            "sandbox spread",
            "geometry gate",
            "4d spread",
        ),
        field_tags=("logos", "gematria", "4d", "gate", "btrack"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json",
                json_pointers=(
                    "/gates/gate_b_geometry_production/recipe_id",
                    "/gates/gate_b_geometry_production/pass",
                    "/research_only",
                ),
            ),
        ),
        related_concepts=(
            "logos_cosmic_anchor_graph_math",
            "logos_spread_sandbox_dynamic_tuning",
            "logos_4d_state_non_gating",
        ),
        lane_hint="oracle",
    ),
)
