#!/usr/bin/env python3
"""Build per-lens NotebookLM upload packs (local disk, deterministic).

Copies a minimal allowlist of repo files into reports/notebooklm_lens_packs_v1/<LENS>/
for Google NotebookLM manual source_add (or MCP add_source type=text in batches).

SSOT layout: docs/NotebookLM_sources_manifest.md — «렌즈별 RAG — 노트북 1목적 매핑»
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_lens_packs_v1"
HAAN_BATCH_INDEX = ROOT / "reports/constitution/btrack_pilot/haan_library_downloads_batch_v1_latest.json"
HAAN_SHARED_PATHS = [
    "reports/constitution/btrack_pilot/haan_library_downloads_batch_v1_latest.json",
    "reports/constitution/btrack_pilot/haan_lens_research_fusion_v1_latest.json",
    "reports/constitution/btrack_pilot/haan_lens_nl_query_sets_v1_latest.json",
    "reports/constitution/btrack_pilot/haan_master_delegation_v1_latest.json",
    "reports/constitution/btrack_pilot/haan_master_nl_insight_brief_v1_latest.md",
    "docs/final/artifacts/haan_lens_coordinate_maps_v1_latest.json",
    "docs/final/artifacts/haan_sasang_paper_crossref_pointers_v1_latest.json",
    "data/corpus/ijeoma/_inventory/cheonyucho_downloads_photo_page_map_v1.json",
    "data/corpus/ijeoma/_inventory/cheonyucho_downloads_photo_inventory_v1.json",
]

# Lens id -> list of paths relative to ROOT (skip silently if missing)
PACKS: dict[str, list[str]] = {
    "OPS_COMMAND_ANCHOR": [
        "docs/NotebookLM_sources_manifest.md",
        "docs/final/CURRENT_OPS_SNAPSHOT.md",
        "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
        "docs/final/RESEARCH_HISTORY_V1.md",
    ],
    "TRACKC_BIZ": [
        "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
        "docs/final/artifacts/MKM_COMMERCIALIZATION_ROADMAP_V1.md",
        "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md",
        "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md",
        "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    ],
    "LENS_MYEONGNI": [
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        "docs/final/MYEONGRI_INSIGHT_SSOT.md",
        "docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md",
        "docs/final/artifacts/MANSE_SAJU_STAGE_LAW_CONTRACT_V0.json",
        "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        "reports/constitution/btrack_pilot/haan_lens_nl_query_sets_v1_latest.json",
        "docs/final/artifacts/myeongri_corpus_coordinate_map_v1_latest.json",
    ],
    "LENS_SASANG": [
        "docs/final/schemas/sasang_emotion_mapping_v1.schema.json",
        "docs/final/schemas/sasang_emotion_mapping_v1.example.json",
        "docs/final/schemas/sasang_music_mapping_v1.schema.json",
        "docs/final/artifacts/notebooklm_lens_sasang_rag_excerpt_v1.md",
        "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
        "docs/final/artifacts/sasang_4agent_monitor_policy_v1.json",
        "docs/final/artifacts/MARKET_SASANG_LENS_V1_CONTRACT.json",
        "docs/final/artifacts/SASANG_INDEPENDENT_LENS_V0_CONTRACT.json",
        "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json",
        "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_p6_gate_v1_latest.json",
        "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json",
        "docs/final/artifacts/notebooklm_lens_sasang_ijoeoma_secondary_proxy_pointer_v1.md",
    ],
    "LENS_LOGOS": [
        "AGENTS.md",
        "docs/final/LOGOS_NOTEBOOK_META_GUIDE.md",
        "reports/constitution/btrack_pilot/haan_lens_nl_query_sets_v1_latest.json",
        "docs/final/artifacts/logos_corpus_coordinate_map_v1_latest.json",
        "docs/final/artifacts/haan_logos_gematria_lexicon_join_v1_latest.json",
    ],
    "MKM_CORE_FACT": [
        "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        "docs/final/MKM_LESSONS_LEARNED_V1.md",
        "docs/final/MKM_CORE_THEORY_V1.md",
        "docs/final/COMPRESSION_SLA_POLICY_V1.md",
        "docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md",
        "docs/final/artifacts/lg_compression_trust_packet_onepager_v1.md",
        "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
        "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
        "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md",
        "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json",
        "docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json",
        "docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json",
        "docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json",
    ],
    "COMPRESSION_BTRACK": [
        "docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md",
        "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        "docs/final/COMPRESSION_SLA_POLICY_V1.md",
        "docs/final/TRACKB_QUATERNION_RESTORE_DECISION_MEMO_V2_2026-04-08.md",
        "docs/final/artifacts/trackb_weekly_gate_recheck_latest.json",
        "docs/final/artifacts/compression_prophecy_bridge_status_v1_latest.json",
        "docs/final/artifacts/btrack_llm_input_bundle_latest.json",
        "docs/final/artifacts/trackb_promotion_precheck_draft_latest.json",
    ],
    "IJEOMA_BTRACK": [
        "reports/constitution/btrack_pilot/comp_ijeoma_btrack_nl_ingest_brief_v1.md",
        "reports/constitution/btrack_pilot/comp_corpus01_readiness_v1.json",
        "reports/constitution/btrack_pilot/comp_sasang_g5_join_poc_v1.json",
        "data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md",
        "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
        "data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md",
        "data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md",
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md",
        "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json",
        "docs/final/NotebookLM_sources_manifest.md",
        "docs/research/raw/IJEOMA_SECONDARY_PROXY_v1.json",
        "docs/research/IJEOMA_SECONDARY_PROXY_LIT_REVIEW_2026-06-26.md",
        "reports/constitution/btrack_pilot/ijeoma_secondary_proxy_merge_v1_latest.json",
        "reports/constitution/btrack_pilot/cheonyucho_physical_anchor_park1985_v1.json",
        "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json",
        "reports/constitution/btrack_pilot/haan_ijoeoma_pdf_grep_batch_v1_latest.json",
        "reports/constitution/btrack_pilot/haan_ijoeoma_pdf_grep_expanded_v1_latest.json",
        "reports/constitution/btrack_pilot/cheonyucho_auto_scout_v1_latest.json",
        "docs/research/raw/CHEONYUCHO_AUTO_SCOUT_v1_nl_proxy.md",
        "docs/research/raw/RHO1998_DONGMUYUGO_HANSI_闡幽草_FOOTNOTE10_EXTRACT_nl_proxy.md",
        "docs/research/raw/T1-LEE-DONGMUYUGO-1999_kyobo_toc_manual_nl_proxy.md",
        "reports/constitution/btrack_pilot/haan_lens_research_fusion_v1_latest.json",
        "docs/final/artifacts/ijeoma_corpus_coordinate_map_v1_latest.json",
        "docs/final/artifacts/haan_sasang_paper_crossref_pointers_v1_latest.json",
        "reports/constitution/btrack_pilot/haan_lens_nl_query_sets_v1_latest.json",
        "docs/final/artifacts/cheonyucho_p0_acquisition_checklist_v1_latest.md",
        "docs/research/raw/CHEONYUCHO_JANGSEOGAK_VOL2_LEE_BIBLIO_TOC_nl_proxy.md",
        "reports/constitution/btrack_pilot/jangseogak_vol2_lee_dongmuyugo_biblio_v1_latest.json",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_JANGSEOGAK_VOL2_LEE_DONGMUYUGO_P145_146_nl_proxy.md",
        "docs/research/raw/HAAN_GREP_DONGMUYUGO_HANSI_闡幽草_MENTION_nl_proxy.md",
        "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_biblio_2026_nl_proxy.md",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_reply_2026_nl_proxy.md",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_reply2_2026_nl_proxy.md",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_PARK1985_NLK_RDF_2026_nl_proxy.md",
        "docs/research/raw/CHEONYUCHO_PHYSICAL_SASANG_CLINICAL_P344_2026_nl_proxy.md",
        "docs/research/raw/JEONG_YONGJAE_ijoeoma_human_2022_youtube_nl_proxy.md",
        "docs/research/raw/IJEOMA_JINHAE_HYEONGAM_career_T1_nl_proxy.md",
        "reports/constitution/btrack_pilot/cheonyucho_dr_vs_t0_question_matrix_v1_latest.json",
        "reports/constitution/btrack_pilot/ijeoma_jinhae_hyeongam_t1_latest.json",
        "reports/constitution/btrack_pilot/jeong_yongjae_ijoeoma_secondary_digest_v1_latest.json",
        "reports/notebooklm_ijoeoma_sasang_source_add_checklist_v1_latest.json",
    ],
    "LENS_PROPHECY": [
        "docs/final/NOTEBOOKLM_PROPHECY_LENS_INDEX_V1.md",
        "docs/final/NOTEBOOKLM_GENERAL_PROPHECY_VPS_GIT_FORESIGHT_BUNDLE_2026-04-11.md",
        "docs/final/NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md",
        "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json",
        "docs/final/BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json",
        "docs/final/artifacts/general_prophecy_brief_latest.md",
        "docs/final/artifacts/btrack_prophecy_score_latest.json",
        "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
        "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
        "docs/final/artifacts/prophecy_restoration_spike_latest.json",
        "docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json",
        "docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md",
        "docs/final/artifacts/ATHENA_SHADOW_LOOP_BTC_FIRST_COMMAND_V1.md",
        "docs/final/artifacts/general_prophecy_latest.json",
        "docs/final/artifacts/prophecy_role_router_multiscenario_opt_30y_btc_neutralbase_latest.json",
        "docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json",
        "docs/final/artifacts/prophecy_2050_two_track_v1_latest.json",
        "docs/final/artifacts/trackc_prophecy_dual_leg_brief_latest.md",
        "reports/prophecy_lane_closure_bundle_v1_latest.json",
    ],
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _haan_proxy_paths_for_lens(lens_key: str) -> list[str]:
    if not HAAN_BATCH_INDEX.is_file():
        return []
    doc = json.loads(HAAN_BATCH_INDEX.read_text(encoding="utf-8"))
    lane_map = {
        "LENS_LOGOS": ("logos", "ijeoma_logos_bridge"),
        "LENS_MYEONGNI": ("myeongri",),
        "IJEOMA_BTRACK": ("ijeoma", "ijeoma_logos_bridge"),
    }
    lanes = lane_map.get(lens_key, ())
    out: list[str] = []
    for item in doc.get("items") or []:
        if item.get("lens") in lanes and isinstance(item.get("nl_proxy"), str):
            out.append(item["nl_proxy"])
    return sorted(set(out))


def _pack_paths(lens_key: str) -> list[str]:
    base = list(PACKS.get(lens_key, []))
    if lens_key in ("LENS_LOGOS", "LENS_MYEONGNI", "IJEOMA_BTRACK"):
        base.extend(HAAN_SHARED_PATHS)
        base.extend(_haan_proxy_paths_for_lens(lens_key))
    # stable dedupe
    seen: set[str] = set()
    merged: list[str] = []
    for rel in base:
        if rel not in seen:
            seen.add(rel)
            merged.append(rel)
    return merged


def main() -> int:
    preserved_map: str | None = None
    map_path = OUT / "notebook_ids.json"
    if map_path.is_file():
        preserved_map = map_path.read_text(encoding="utf-8")
    elif HAAN_BATCH_INDEX.parent.exists():
        template_map = ROOT / "docs/final/notebooklm_lens_pack_push_map_v1.template.json"
        if template_map.is_file():
            preserved_map = template_map.read_text(encoding="utf-8")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    if preserved_map:
        map_path.write_text(preserved_map, encoding="utf-8")

    index: dict[str, Any] = {
        "schema": "notebooklm_lens_packs_v1",
        "version": "1.0.0",
        "root": str(OUT),
        "packs": {},
    }

    for lens in PACKS:
        rels = _pack_paths(lens)
        lens_dir = OUT / lens
        lens_dir.mkdir(parents=True, exist_ok=True)
        files_out: list[dict[str, Any]] = []
        for rel in rels:
            src = ROOT / rel.replace("\\", "/")
            if not src.is_file():
                files_out.append({"rel": rel, "status": "missing"})
                continue
            dest = lens_dir / rel.replace("/", "__")
            shutil.copy2(src, dest)
            files_out.append(
                {
                    "rel": rel,
                    "status": "copied",
                    "dest": str(dest.relative_to(OUT)),
                    "bytes": dest.stat().st_size,
                    "sha256": _sha256(dest),
                }
            )
        index["packs"][lens] = {"files": files_out}

    readme = OUT / "README.md"
    readme.write_text(
        """# NotebookLM lens packs (auto-generated)

Run from repo root:

```bash
py scripts/build_notebooklm_lens_source_packs_v1.py
```

Then in Google NotebookLM: create one notebook per lens (see `docs/NotebookLM_sources_manifest.md`), and **source_add** each file under the matching folder (`LENS_MYEONGNI/`, …). Do not upload personal birth data as files; keep `[HYPO]` in prompts only.

**Optional — `nlm` CLI batch push (same stack as `Push-NotebooklmFusionHubBulk.ps1`):**

1. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Push-NotebooklmLensPacks_v1.ps1 -InitMap` → creates `reports/notebooklm_lens_packs_v1/notebook_ids.json` from `docs/final/notebooklm_lens_pack_push_map_v1.template.json` (edit UUIDs per your NL notebooks).
2. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Push-NotebooklmLensPacks_v1.ps1 -DryRun` (plan only; no `nlm` required).
3. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Push-NotebooklmLensPacks_v1.ps1` (requires `nlm` on PATH + Google auth for that CLI profile).

""",
        encoding="utf-8",
    )

    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}", file=sys.stderr)
    print(json.dumps({"pack_root": str(OUT), "lenses": list(PACKS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
