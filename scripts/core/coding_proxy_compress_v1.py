"""Coding proxy compress: structured block preserve + evaluate_report body."""
from __future__ import annotations

from typing import Any

from scripts.core.coding_proxy_context_v1 import (
    build_coding_must_keep,
    compressible_has_structured_blocks,
    merge_compressed_with_preserved,
    partition_coding_text,
)
from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
from scripts.report_multilens_performance_eval import evaluate_report

_BASE_MUST_KEEP = frozenset({"사상의학", "체질", "sasang", "myeongni", "bible"})


def _maybe_attach_meta_sidecar(
    result: dict[str, Any],
    text: str,
    *,
    lane: str | None,
) -> dict[str, Any]:
    """B-track optional: MKM_PRISM_META_CHANNEL_BTRACK=1 adds Prism sidecar (default off)."""
    try:
        from scripts.sandbox.coding_proxy_meta_channel_v1 import enrich_with_meta_sidecar

        return enrich_with_meta_sidecar(result, text, lane=lane)
    except Exception:
        return result


def _baseline_jaccard() -> float:
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[2] / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
    if not path.is_file():
        return 0.0
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return float(doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))


def _profile_for_lane(base: dict[str, Any], lane: str | None, lane_intensity: dict[str, str]) -> dict[str, Any]:
    prof = dict(base)
    if lane and lane in lane_intensity:
        prof["intensity"] = lane_intensity[lane]
    return prof


def _compressed_effective(text: str, profile: dict[str, Any], must_keep: set[str]) -> tuple[str, dict[str, Any]]:
    doc = {
        "compression_cases": [
            {"id": "coding-proxy", "raw_text": text, "compressed_text": "", "reconstructed_text": ""}
        ],
        "fusion_answer_cases": [],
    }
    _bp = env_apply_gematria_4d_bridge_policy()
    report = evaluate_report(
        doc,
        source_input="btrack:coding_proxy_compress_v1",
        mode="experimental",
        strategy=str(profile.get("strategy", "A")),
        intensity=str(profile.get("intensity", "extreme")),
        must_keep=must_keep,
        jaccard_drop_threshold_pp=1.5,
        baseline_avg_jaccard=_baseline_jaccard(),
        general_max_saving_rate=profile.get("general_max_saving_rate"),
        sensitive_max_saving_rate=profile.get("sensitive_max_saving_rate"),
        hangul_max_saving_rate=profile.get("hangul_max_saving_rate"),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=_bp,
        include_gematria_4d_bridge=_bp,
        include_cee_core=_bp,
        apply_gematria_4d_bridge_policy=_bp,
    )
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    first = cases[0] if cases and isinstance(cases[0], dict) else {}
    surface = str(first.get("compressed_text_effective") or first.get("compressed_text") or "")
    return surface, first


def coding_proxy_compress_surface(
    text: str,
    profile: dict[str, Any],
    *,
    lane: str | None,
    lane_intensity: dict[str, str],
) -> dict[str, Any]:
    """Return agent-facing compressed surface with structured blocks preserved."""
    prof = _profile_for_lane(profile, lane, lane_intensity)
    must_keep = set(_BASE_MUST_KEEP) | build_coding_must_keep(text)

    if compressible_has_structured_blocks(text):
        compressible, preserved = partition_coding_text(text)
        body = compressible if compressible else text
        compressed_part, case_metrics = _compressed_effective(body, prof, must_keep)
        surface = merge_compressed_with_preserved(compressed_part, preserved)
        raw_tok = int(case_metrics.get("raw_tokens") or 0)
        comp_tok = int(case_metrics.get("compressed_tokens") or 0)
        # Approximate full-surface saving using body compression + preserved verbatim.
        from scripts.run_cursor_coding_compress_bench_v1 import _token_in

        full_in = _token_in(text)
        full_out = _token_in(surface)
        saving = 1.0 - (full_out / full_in) if full_in > 0 else 0.0
        return _maybe_attach_meta_sidecar(
            {
                "surface": surface,
                "proxy_path": "structured_preserve_compress",
                "structured_preserve": True,
                "preserved_block_count": len(preserved),
                "preserved_blocks": preserved,
                "global_token_saving_rate": saving,
                "reconstruction_fidelity_jaccard": float(
                    case_metrics.get("reconstruction_fidelity_jaccard") or 0.0
                ),
                "raw_tokens": full_in,
                "compressed_tokens": full_out,
                "intensity_used": prof.get("intensity"),
            },
            text,
            lane=lane,
        )

    from scripts.run_cursor_coding_compress_bench_v1 import _eval_proxy_aligned

    metrics = _eval_proxy_aligned(text, profile, lane=lane, lane_intensity=lane_intensity)
    comp_part, _ = _compressed_effective(text, prof, must_keep)
    return _maybe_attach_meta_sidecar(
        {
            "surface": comp_part,
            "structured_preserve": False,
            **metrics,
        },
        text,
        lane=lane,
    )
