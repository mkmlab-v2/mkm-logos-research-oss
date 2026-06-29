#!/usr/bin/env python3
"""Materialize [HYPO] GPU hybrid transition 1-page spec (dual rail, no active write)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/mkm_gpu_hybrid_transition_spec_v1.schema.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file() or (ROOT / rel).is_file()


def main() -> int:
    doc: dict = {
        "schema": "mkm_gpu_hybrid_transition_spec_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "one_page_summary_ko": (
            "GPU는 단일 루프로 41k·31k를 합치지 않는다. 압축 Track A는 41k 동결 KPI와 GPU semantic을 "
            "병렬 측정한 뒤 검증 시에만 41k 선을 단계 차단한다. 31k 원문 SSOT는 폐기하지 않고 "
            "벡터/ANN 레이어만 추가한다."
        ),
        "constitution_meta": {
            "route_setting": "선로 ① 고정 / ② 패시브",
            "track_a_strict_lock": True,
            "fail_comp_004_summary": "repair-only·1103·B-track uplift를 Track A·live·MS 헤드라인에 자동 합선 금지",
            "mission_log_section": "MISSION_LOG.md §작전 지휘선 바인딩",
        },
        "rails_comparison": [
            {
                "rail_id": "compression_41k",
                "asset_label": "41k (~41,658행 master_codebook_lexicon_v1)",
                "primary_role": "Track A 압축 must_keep lookup 연료 (4D policy OFF 동결)",
                "frozen_now": "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json · Golden-40 ~47.5% / J ~0.89",
                "gpu_transition_shape": "41k 백업 유지 + GPU semantic 병렬 측정 → 검증 후 단계적 41k 선 차단",
                "single_loop_merge_forbidden": True,
            },
            {
                "rail_id": "prophecy_shadow_31k",
                "asset_label": "31k (~31,102절 원문 SSOT)",
                "primary_role": "31k41k shadow 모의시험 · [RESEARCH_ONLY] · [NON_GATING]",
                "frozen_now": "run_btrack_31k41k_prophecy_shadow_chain_v1.py E2E · allowlist_review 게이트",
                "gpu_transition_shape": "31k 텍스트 SSOT 유지 + 벡터/ANN 검색 레이어 추가 (환각·가짜 절 금지)",
                "single_loop_merge_forbidden": True,
            },
        ],
        "rail_compression_41k": {
            "lane": "Track A · compression · 선로 ② GPU PoC",
            "lexicon_row_count": 41658,
            "frozen_kpi_pointer": {
                "active_report": _rel(
                    ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
                ),
                "bench_input": _rel(
                    ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
                ),
                "headline_external_rounded": "47.5% saving · Jaccard ~0.89 (Fact-Lock; not MS paste alone)",
            },
            "lexicon_bridge_script": _rel(
                ROOT / "scripts/core/master_codebook_lexicon_v1_bridge.py"
            ),
            "parallel_gpu_poc": {
                "script": _rel(ROOT / "scripts/run_en_tech_semantic_gpu_poc_v1.py"),
                "bundle": _rel(ROOT / "scripts/Run-MkmGpuRecommendedBundle_v1.ps1"),
                "latest_artifact": _rel(
                    ROOT
                    / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
                ),
                "oov_patch_artifact": _rel(
                    ROOT
                    / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_v1_latest.json"
                ),
                "note": "en_tech zone PoC; not full 41k replacement until beat_frozen + human sign-off",
            },
            "hybrid_protocol": {
                "phase": "parallel_ablation",
                "metrics_required": [
                    "global_token_saving_rate",
                    "avg_reconstruction_fidelity_jaccard",
                ],
                "reporting": "raw vs repair_v2 if repair layer touched; never collapse to single headline",
                "same_bench": "MULTILENS_PERFORMANCE_EVAL_INPUT_V2 40 cases",
                "lexicon_ablation_script": _rel(
                    ROOT / "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"
                ),
            },
            "retire_gate": {
                "41k_disconnect_allowed": False,
                "conditions_all_required": [
                    "GPU path beats frozen Golden-40 on same 40-case bench (documented JSON)",
                    "human_signoff on MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
                    "TRACK_A_STRICT_LOCK explicitly released by commander order",
                ],
                "until_then": "41k pointer + bridge remain production_ssot",
            },
            "recent_audit_pointer": _rel(
                ROOT / "reports/lexicon_lookup_exception_audit_v1_latest.json"
            ),
        },
        "rail_prophecy_shadow_31k": {
            "lane": "B-track · prophecy · 31k41k shadow",
            "verse_count_ssot": 31102,
            "corpus_disambiguation": (
                "학계 ~31k 절 통계와 MKM 운영 분모 혼용 금지; 41,658는 lexicon row 수와 별 단위"
            ),
            "shadow_chain": {
                "daily_fast": "py scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py --daily-fast",
                "spec_md": _rel(
                    ROOT
                    / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_experiment_spec_v1_latest.md"
                ),
                "allowlist_gate": "check_btrack_31k41k_prophecy_shadow_gate_v1.py --gate-mode allowlist_review",
                "tags": ["[RESEARCH_ONLY]", "[NON_GATING]"],
            },
            "vector_layer_additive": {
                "corpus_retire_forbidden": True,
                "allowed_evolution": "embedding index · ANN-lite query over fixed verse SSOT",
                "hallucination_guard": "no synthetic verse IDs; retrieval-only over 31k anchor",
                "implementation_status": "partial_b_track_skeleton",
            },
            "logos_vector_infra_pointers": [
                _rel(ROOT / "scripts/build_logos_vector_index_manifest_v1.py"),
                _rel(ROOT / "scripts/build_logos_vector_index_ann_lite_v1.py"),
                _rel(
                    ROOT
                    / "docs/final/artifacts/logos_vector_index_manifest_v1_latest.json"
                ),
            ],
        },
        "forbidden": [
            "single_gpu_loop merging compression_41k and prophecy_shadow_31k pipelines",
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from GPU PoC or this spec",
            "promote Track A·live·MS from repair_v2·1103 matrix·en_tech PoC alone",
            "delete or replace 31,102-verse SSOT with model-generated text",
            "retire 41k lexicon before parallel bench beat + human sign-off",
            "use 13k/14k informal labels in external copy instead of Golden-40·41k·31k",
        ],
        "dod_exit_criteria": [
            {
                "criterion_id": "DOD-C41K-PARALLEL",
                "rail_id": "compression_41k",
                "description": "41k ON/OFF and GPU semantic PoC documented on same V2 bench with delta JSON",
                "commands_optional": [
                    "py scripts/comp_atom02_lexicon_must_keep_analysis_v1.py",
                    "py scripts/run_en_tech_semantic_gpu_poc_v1.py",
                ],
                "evidence_paths": [
                    _rel(
                        ROOT
                        / "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"
                    ),
                    _rel(
                        ROOT
                        / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
                    ),
                ],
                "human_signoff_required": True,
            },
            {
                "criterion_id": "DOD-31K-SHADOW-OBS",
                "rail_id": "prophecy_shadow_31k",
                "description": "31k41k shadow daily-fast chain exit 0; allowlist gate discipline unchanged",
                "commands_optional": [
                    "py scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py --daily-fast",
                ],
                "evidence_paths": [
                    _rel(
                        ROOT
                        / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_experiment_spec_v1_latest.md"
                    ),
                ],
                "human_signoff_required": False,
            },
            {
                "criterion_id": "DOD-GPU-BUNDLE-SMOKE",
                "rail_id": "cross_cutting",
                "description": "GpuRecommendedBundle smoke exit 0 when infra available (oracle + Pack 0-B)",
                "commands_optional": [
                    "powershell -File scripts/Run-MkmGpuRecommendedBundle_v1.ps1",
                ],
                "evidence_paths": [
                    _rel(ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"),
                ],
                "human_signoff_required": False,
            },
        ],
        "guardrails": [
            "This file is [HYPO] planning SSOT only; CONSTITUTION paths remain implementation fact SSOT",
            "P0 verify_p0_constitution_gate_paths.ps1 exit 0 does not prove prediction or GPU promotion",
            "Azure/Lab/NVIDIA infra waits stay passive (선로 ②) unless commander orders",
        ],
    }

    missing = [p for block in doc["dod_exit_criteria"] for p in block["evidence_paths"] if not _exists(p)]
    doc["path_check"] = {
        "dod_evidence_all_present": len(missing) == 0,
        "missing_optional_note": missing[:8],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "schema": _rel(SCHEMA), "missing_count": len(missing)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
