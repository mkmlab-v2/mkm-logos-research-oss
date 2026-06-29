"""Design domain adapter LTM graph concepts ([HYPO] routing)."""

from __future__ import annotations

from mkm_long_term_memory_graph_lib_v1 import ConceptSpec, CoordinateSpec

DESIGN_ADAPTER_CONCEPT_SPECS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        concept_id="pixel_battalion_adapter",
        label_ko="Pixel Battalion adapter · mkmlife sprite gate",
        essence="MKM_PIXEL_LANGUAGE · local/cdn dual-mode · sprite URL hard gate · design lane",
        must_keep_tags=("[HYPO]", "overall_ok", "track_wall"),
        query_aliases=(
            "pixel",
            "pixel battalion",
            "sprite",
            "mkmlife",
            "MKM_PIXEL_LANGUAGE",
            "sprite_url",
        ),
        field_tags=("design", "pixel", "showroom", "mkmlife", "btrack"),
        priority=6,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/mkmlife_pixel_sprite_urls_gate_v1_latest.json",
                json_pointers=(
                    "/overall_ok",
                    "/track_wall",
                    "/hypothesis_tag",
                    "/lane",
                ),
            ),
        ),
        related_concepts=("design_showroom_domain_portfolio", "domain_adapters_shallow_routing"),
        lane_hint="design",
    ),
    ConceptSpec(
        concept_id="lens_audio_adapter",
        label_ko="Lens Audio adapter · BGM gate · lens_safe_tempo_clamp",
        essence="audio_bgm_gate · economy chain · lens_safe_tempo_clamp PoC · design lane",
        must_keep_tags=("lens_alignment_pass", "decision", "track"),
        query_aliases=(
            "lens audio",
            "bgm",
            "musicgen",
            "tempo",
            "lens_safe_tempo",
            "audio gate",
        ),
        field_tags=("design", "audio", "bgm", "music", "lens", "btrack"),
        priority=6,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="reports/audio_gate_latest.json",
                json_pointers=(
                    "/decision",
                    "/track",
                    "/metrics/lens_alignment_pass",
                ),
            ),
        ),
        related_concepts=("design_showroom_domain_portfolio", "domain_adapters_shallow_routing"),
        lane_hint="design",
    ),
    ConceptSpec(
        concept_id="domain_adapters_shallow_routing",
        label_ko="Domain adapters · shallow routing SSOT",
        essence="sync_bridge domain_adapters + ops_memory overlay + route_mkm_ops_memory_pack",
        must_keep_tags=("domain_adapters", "pixel_battalion", "lens_audio"),
        query_aliases=(
            "shallow routing",
            "domain adapter",
            "jagged intelligence",
            "deep fetch",
            "ops_memory overlay",
        ),
        field_tags=("meta_routing", "design", "packaging", "btrack"),
        priority=7,
        coordinates=(
            CoordinateSpec(
                kind="json_pointer",
                file_path="docs/final/artifacts/mkm_ops_sync_bridge_v1.json",
                json_pointers=(
                    "/domain_adapters/routing_lane_default",
                    "/domain_adapters/one_click_smoke_ps1",
                    "/domain_adapters/adapters/0/id",
                    "/domain_adapters/adapters/1/id",
                ),
            ),
        ),
        related_concepts=("pixel_battalion_adapter", "lens_audio_adapter", "ltm_graph_self_meta"),
        lane_hint="design",
    ),
)
