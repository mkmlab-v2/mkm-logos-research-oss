#!/usr/bin/env python3
"""Bundle Logos Track B integration artifacts into MS evidence pack (optional lane)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MS_PACK = ROOT / "reports/external_validation_ms_evidence_pack_v1_latest"
SUBDIR = "logos_track_b"
POINTER_NAME = "ms_track_b_logos_internal_pointer_v1.txt"

BUNDLE_FILES = [
    "reports/logos_track_b_integration_closure_v1_latest.json",
    "reports/logos_track_b_phase_i_v1_latest.json",
    "reports/logos_track_b_phase_l_v1_latest.json",
    "reports/logos_track_b_phase_k_v1_latest.json",
    "reports/logos_track_b_themed_deep_push_v1_latest.json",
    "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json",
    "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json",
    "reports/logos_insight_synthesis_digest_v1_latest.md",
    "reports/logos_track_b_phase_n_v1_latest.json",
    "reports/logos_cross_theme_invariant_bridge_v1_latest.json",
    "reports/logos_multi_insight_synthesis_v1_latest.json",
    "reports/logos_phase_o_digest_v1_latest.md",
    "reports/logos_track_b_phase_o_v1_latest.json",
    "reports/logos_track_b_research_v1_latest.json",
    "reports/logos_b2b_deterministic_chain_v1_latest.json",
    "reports/logos_phase_o_completion_gate_v1_latest.json",
    "reports/logos_track_b_hot_reload_v1_latest.json",
    "docs/final/artifacts/logos_neuro_symbolic_b2b_public_one_pager_ko_v1.md",
    "docs/final/artifacts/logos_neuro_symbolic_b2b_gtm_pointer_v1_latest.json",
    "reports/logos_research_commercial_pack_v1_latest.json",
    "reports/logos_research_product_metrics_v1_latest.json",
    "docs/final/artifacts/logos_research_commercial_product_v1_latest.json",
    "reports/logos_lexicon_4d_v1_latest.json",
    "reports/logos_41k_4d_reclassification_audit_v1_latest.json",
    "reports/logos_lexicon_4d_research_audit_v1_latest.json",
    "reports/verse_metadata_shadow_v1_latest.json",
    "reports/verse_metadata_shadow_v2_latest.json",
    "reports/term_postit_shadow_v2_latest.json",
    "reports/logos_bidirectional_anchor_index_v1_latest.json",
    "reports/shadow_postits_quality_gate_v1_latest.json",
    "reports/tracka_logic_weights_shadow_v1_latest.json",
    "reports/compression_perf_test_v1_latest.json",
    "reports/optimization_impact_v1_latest.json",
    "reports/tracka_shadow_sweep_v1_latest.json",
    "reports/tracka_shadow_default_preset_v1_latest.json",
    "reports/tracka_logic_weights_shadow_preset_v1_latest.json",
    "reports/compression_perf_test_preset_v1_latest.json",
    "reports/optimization_impact_preset_v1_latest.json",
    "reports/dss_apocrypha_shadow_lane_pilot_plan_v1_latest.json",
    "reports/dss_apocrypha_shadow_lane_v1_latest.json",
    "reports/dss_shadow_alignment_v1_latest.json",
    "reports/apocrypha_shadow_alignment_v1_latest.json",
    "reports/shadow_lane_appendix_gematria_v1_latest.json",
    "reports/shadow_canon_gematria_xref_map_v1_latest.json",
    "reports/shadow_lane_appendix_gematria_chain_v1_latest.json",
    "docs/final/artifacts/shadow_lane_gematria_gate_v1_latest.json",
    "reports/shadow_appendix_id_bridge_v1_latest.json",
    "reports/shadow_cross_lane_gematria_audit_v1_latest.json",
    "reports/shadow_cross_lane_gematria_audit_v1_latest.md",
    "reports/shadow_cross_lane_gematria_chain_v1_latest.json",
    "docs/final/artifacts/shadow_cross_lane_gematria_gate_v1_latest.json",
    "reports/dss_11q5_line_witness_map_v1_latest.json",
    "reports/shadow_line_witness_registry_v1_latest.json",
    "reports/dss_11q5_line_witness_chain_v1_latest.json",
    "reports/dss_line_witness_verification_scan_v1_latest.json",
    "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json",
    "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json",
    "reports/dss_line_witness_verification_operator_board_v1_latest.json",
    "reports/dss_line_witness_verification_operator_board_v1_latest.md",
    "reports/dss_line_witness_verification_chain_v1_latest.json",
    "reports/cross_ref_entry_12_mt_only_sidecar_v1_latest.json",
    "reports/cross_ref_entry_12_13_bench_relabel_sidecar_v1_latest.json",
    "reports/dss_4q_ps5_line_witness_map_v1_latest.json",
    "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
    "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json",
    "reports/manuscript_integrity_audit_11q5_psalms_commander_v1_latest.md",
    "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json",
    "reports/p5_manuscript_integrity_chain_v1_latest.json",
    "reports/p6_post_manuscript_integrity_chain_v1_latest.json",
    "reports/entry_13_external_witness_research_draft_v1_latest.json",
    "reports/entry_13_external_witness_research_draft_v1_latest.md",
    "reports/enterprise_apply_live_smoke_v1_latest.json",
    "reports/compression_open_bench_minimal_command_set_v1_latest.json",
    "reports/compression_open_bench_minimal_command_set_v1_latest.md",
    "reports/commander_delegation_m_auto_v1_latest.json",
    "docs/final/artifacts/commander_delegation_m_signoff_v1_latest.json",
    "reports/commander_delegation_m_apply_v1_latest.json",
    "docs/final/artifacts/entry_13_commander_scholarly_promotion_signoff_v1_latest.json",
    "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json",
    "reports/entry_13_post_promotion_commander_report_v1_latest.json",
    "reports/entry_13_post_promotion_commander_report_v1_latest.md",
    "reports/entry_13_post_promotion_closure_chain_v1_latest.json",
    "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json",
    "reports/logos_macula_themed_ingest_v1_latest.json",
    "docs/final/artifacts/logos_commercial_finish_closure_v1_latest.json",
    "docs/final/artifacts/compression_open_bench_logos_audit_smoke_v1_latest.json",
    "docs/final/artifacts/logos_rag_integrity_audit_one_pager_b2b_v1_latest.md",
    "reports/logos_track_b_commercial_finish_v1_latest.json",
    "reports/logos_canon_book_coverage_heatmap_v1_latest.json",
    "reports/logos_lexicon_4d_dual_ab_report_v1_latest.json",
    "reports/logos_track_b_commercial_depth_closure_v1_latest.json",
    "reports/logos_track_b_multi_theme_commander_digest_latest.md",
    "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json",
    "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json",
    "reports/external_validation_ms_evidence_pack_v1_latest/ms_b2b_logos_logic_verifier_appendix_v1.md",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _pointer_text(closure: dict[str, Any]) -> str:
    gates = closure.get("gates") or {}
    metrics = closure.get("metrics") or {}
    lines = [
        "[MS 팩 — Logos Track B 내부 포인터 · 헤드라인 합산 금지]",
        "",
        "lane: track_b_hypo · NON_GATING · research_only",
        f"integration_closure_ok: {closure.get('ok')}",
        f"graphrag_seed_organic: {metrics.get('graphrag_seed_organic')}",
        f"topic_graphrag_seed_hits: {metrics.get('topic_graphrag_seed_hits')} (6-topic diagnostic)",
        f"llm_citation_valid_themes: {metrics.get('llm_citation_valid_themes')}",
        f"b2b_promoted_claims: {metrics.get('b2b_promoted_claims')}",
        f"track_a_bridge: {gates.get('track_a_bridge', False)}",
        "",
        "[상용 SKU 표면 · 헤드라인 합산 금지]",
        "public_domain: logos.jema-ai.com",
        "manifest: docs/final/artifacts/logos_research_commercial_product_v1_latest.json",
        "",
        "[번들 폴더]",
        f"reports/external_validation_ms_evidence_pack_v1_latest/{SUBDIR}/",
        "",
        "[재현]",
        "py scripts/run_logos_track_b_phase_j_v1.py",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-dir", type=Path, default=MS_PACK)
    args = ap.parse_args()

    if not args.pack_dir.is_dir():
        raise SystemExit(f"MS pack missing: {args.pack_dir} — run build_external_validation_ms_evidence_pack_v1.py first")

    dest_dir = args.pack_dir / SUBDIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    bundled: list[dict[str, str]] = []
    missing: list[str] = []
    for rel in BUNDLE_FILES:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = dest_dir / src.name
        shutil.copy2(src, dst)
        bundled.append(
            {
                "source": rel.replace("\\", "/"),
                "bundled": str(dst.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    closure = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")
    pointer_path = args.pack_dir / POINTER_NAME
    pointer_path.write_text(_pointer_text(closure), encoding="utf-8")

    manifest_path = args.pack_dir / "manifest.json"
    manifest = _load(manifest_path)
    if not manifest:
        raise SystemExit("manifest.json missing in MS pack")

    manifest["track_b_logos_bundle"] = {
        "schema": "ms_evidence_pack_track_b_logos_bundle_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "headline_merge_forbidden": True,
        "pointer": str(pointer_path.relative_to(ROOT)).replace("\\", "/"),
        "subdir": str(dest_dir.relative_to(ROOT)).replace("\\", "/"),
        "files": bundled,
        "missing_sources": missing,
        "reproduce": "py scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py",
    }
    manifest["generated_at_utc"] = _utc()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(bundled) >= 4 and closure.get("ok") is True
    print(
        json.dumps(
            {
                "ok": ok,
                "bundled": len(bundled),
                "missing": missing,
                "pointer": str(pointer_path.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
