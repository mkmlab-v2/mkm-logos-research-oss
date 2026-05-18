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
        "docs/final/artifacts/business_registration_plan_v1.md",
        "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md",
        "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md",
        "docs/final/artifacts/moksori_mega_commercialization_roadmap_from_repo_ssot_v1.md",
    ],
    "LENS_MYEONGNI": [
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        "docs/final/MYEONGRI_INSIGHT_SSOT.md",
        "docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md",
        "docs/final/artifacts/MANSE_SAJU_STAGE_LAW_CONTRACT_V0.json",
        "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
    ],
    "LENS_SASANG": [
        "docs/final/schemas/sasang_emotion_mapping_v1.schema.json",
        "docs/final/schemas/sasang_emotion_mapping_v1.example.json",
    ],
    "LENS_LOGOS": [
        "AGENTS.md",
        "docs/final/LOGOS_NOTEBOOK_META_GUIDE.md",
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


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    index: dict[str, Any] = {
        "schema": "notebooklm_lens_packs_v1",
        "version": "1.0.0",
        "root": str(OUT),
        "packs": {},
    }

    for lens, rels in PACKS.items():
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
