"""Shared Logos cosmic anchor row builder (S,L,K,M SSOT; thermo alias optional)."""

from __future__ import annotations

import hashlib
from typing import Any

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
from scripts.core.gematria_to_4d_bridge_sandbox_v1 import (
    RECIPE_ID as SANDBOX_RECIPE_ID,
    build_gematria_4d_bridge_sandbox,
)
from scripts.core.gematria_thermo_alias_v1 import thermo_alias_from_spec
from scripts.core.normalize_gematria_to_kernel_v1 import (
    NORMALIZE_FN,
    kernel_drafts_from_4d,
    rank_primitive_alignments,
    rank_primitive_alignments_spread_aware,
)

FACT_LOCK = {
    "hypothesis_class": "HYPO",
    "rail": "B_TRACK",
    "non_gating": True,
    "forbidden_synthesis": True,
    "ready_for_external_send": False,
    "disclaimer_ko": (
        "[HYPO] gematria 4D ↔ kernel draft resonance row. "
        "신학·체질·운세 단정 아님. Track A·live·SEND 금지."
    ),
}

TRACK_WALL = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def gematria_inputs(spec: dict[str, Any]) -> tuple[str, str, str, str]:
    texts = spec.get("gematria_texts")
    if isinstance(texts, dict):
        raw = str(texts.get("raw") or spec.get("gematria_text", ""))
        compressed = str(texts.get("compressed") or spec.get("gematria_text", raw))
        reconstructed = str(texts.get("reconstructed") or compressed)
        return raw, compressed, reconstructed, raw
    text = str(spec.get("gematria_text", ""))
    return text, text, text, text


def build_anchor_row(
    spec: dict[str, Any],
    *,
    generated_at_utc: str,
    compute_thermo_alias: bool = False,
    spread_aware_ranking: bool = False,
    use_sandbox_bridge: bool = False,
) -> dict[str, Any]:
    raw_text, compressed_text, reconstructed_text, canonical_text = gematria_inputs(spec)
    meta = build_gematria_metadata(
        raw_text=raw_text,
        compressed_text=compressed_text,
        reconstructed_text=reconstructed_text,
    )
    prod_bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    if use_sandbox_bridge:
        bridge = build_gematria_4d_bridge_sandbox(gematria_metadata=meta)
        vector_4d = bridge["vector_4d"]
        recipe_id = SANDBOX_RECIPE_ID
    else:
        bridge = prod_bridge
        vector_4d = bridge["vector_4d"]
        recipe_id = "gematria_bridge_v1"
    legacy = spec.get("legacy_thermo_alias")
    if compute_thermo_alias or legacy is None:
        legacy = thermo_alias_from_spec(spec)

    if spread_aware_ranking:
        alignments = rank_primitive_alignments_spread_aware(
            vector_4d,
            thermo_alias=legacy,
            top_n=3,
        )
        normalize_fn = f"{NORMALIZE_FN}::spread_aware_v1"
    else:
        alignments = rank_primitive_alignments(vector_4d, top_n=3)
        normalize_fn = NORMALIZE_FN

    return {
        "schema": "logos_cosmic_anchor_formalization_v1",
        "version": "1.0.0",
        "anchor_id": spec["anchor_id"],
        "verse_refs": spec.get("verse_refs") or [],
        "motif_lemma": spec.get("motif_lemma") or {},
        "fact_lock": dict(FACT_LOCK),
        "layers": {
            "logos_layer": {
                "summary_ko": spec.get("logos_summary_ko", ""),
                "citation_refs": spec.get("verse_refs") or [],
                "interpretive_class": "motif_note",
            },
            "sasang_myeongni_layer": {
                "summary_ko": spec.get("sasang_summary_ko", ""),
                "ssot_refs": [
                    "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json",
                    "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
                ],
                "constitution_hint": spec.get("constitution_hint", "none"),
                "ohaeng_hint": spec.get("ohaeng_hint", "none"),
            },
        },
        "text_span": {
            "unit": "verse" if spec.get("gematria_texts") else "motif_lemma",
            "original_script_text": canonical_text,
            "text_sha256": sha256_text(canonical_text),
        },
        "gematria_v1": {
            "method": "mispar_hechrachi_additive",
            "hebrew_value": int(meta.get("raw_hebrew_sum", 0)),
            "greek_value": int(meta.get("raw_greek_sum", 0)),
            "total_value": int(meta.get("raw_combined_sum", 0)),
        },
        "vector_4d": vector_4d,
        "vector_4d_production": prod_bridge["vector_4d"] if use_sandbox_bridge else None,
        "legacy_thermo_alias": legacy,
        "mapping": {
            "recipe_id": recipe_id,
            "production_recipe_id": "gematria_bridge_v1",
            "thermo_alias_recipe_id": "gematria_thermo_alias_v1",
            "normalize_fn": normalize_fn,
            "generated_at_utc": generated_at_utc,
            "state16_nearest": bridge.get("state16"),
            "distance_to_state16": bridge.get("distance_to_state16"),
            "sandbox_spread_divisor": bridge.get("spread_divisor"),
        },
        "kernel_alignment": alignments,
        "conflict_resolution": spec.get("conflict_resolution") or {"pair_kind": "none"},
        "track_wall": dict(TRACK_WALL),
        "_builder_meta": {
            "kernel_drafts_full": kernel_drafts_from_4d(vector_4d),
            "gematria_metadata": meta,
        },
    }


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in row.items() if not k.startswith("_")}
    if out.get("vector_4d_production") is None:
        out.pop("vector_4d_production", None)
    return out
