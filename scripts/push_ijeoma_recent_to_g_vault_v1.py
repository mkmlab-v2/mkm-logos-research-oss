#!/usr/bin/env python3
"""Mirror recent IJEOMA B-track corpus (2026-06-24 batch) to G: MKM_DATA_VAULT."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_g_vault_manual_sync_2026-06-24.json"

# (workspace_rel, vault_rel_under_MKM_DATA_VAULT)
COPIES: list[tuple[str, str]] = [
    (
        "data/corpus/ijeoma/originals/geukchigo_partial/GEUKCHIGO_vol1_preface_ruyo_1-1_user_paste_2026-06-24.md",
        "data/corpus/ijeoma/originals/geukchigo_partial/GEUKCHIGO_vol1_preface_ruyo_1-1_user_paste_2026-06-24.md",
    ),
    (
        "data/corpus/ijeoma/originals/geukchigo_partial/GEUKCHI_DSSBW_SASIMSIMMUL_BRIDGE_commentary_user_paste_2026-06-24.md",
        "data/corpus/ijeoma/originals/geukchigo_partial/GEUKCHI_DSSBW_SASIMSIMMUL_BRIDGE_commentary_user_paste_2026-06-24.md",
    ),
    (
        "data/corpus/ijeoma/_inventory/geukchigo_partial_ingest_v1.json",
        "data/corpus/ijeoma/_inventory/geukchigo_partial_ingest_v1.json",
    ),
    (
        "data/corpus/ijeoma/_inventory/geukchigo_dssbw_bridge_commentary_v1.json",
        "data/corpus/ijeoma/_inventory/geukchigo_dssbw_bridge_commentary_v1.json",
    ),
    (
        "docs/research/CHEONYUCHO_JEMA_MERGED_LIT_REVIEW_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_JEMA_MERGED_LIT_REVIEW_2026-06-24.md",
    ),
    (
        "docs/research/raw/CHEONYUCHO_gemini_report.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_gemini_report.md",
    ),
    (
        "docs/research/raw/CHEONYUCHO_JEMA_BIBLIO_SWEEP_v1.json",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_JEMA_BIBLIO_SWEEP_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_acquisition_probe_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_run_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_acquisition_probe_run_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_park1985_nl_probe_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_park1985_nl_probe_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_acquisition_gate_v1_latest.json",
    ),
    (
        "reports/constitution/btrack_pilot/ijeoma_storage_locations_probe_2026-06-24.json",
        "data/corpus/ijeoma/_inventory/ijeoma_storage_locations_probe_2026-06-24.json",
    ),
    (
        "reports/constitution/btrack_pilot/ijeoma_fdrive_manual_sync_2026-06-24.json",
        "data/corpus/ijeoma/_inventory/ijeoma_fdrive_manual_sync_2026-06-24.json",
    ),
    (
        "docs/research/raw/CHEONYUCHO_scispace_sweep_2026-06-24.json",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_scispace_sweep_2026-06-24.json",
    ),
    (
        "docs/research/raw/LEE_KYUNGLOCK_2005_JEMA_MEDICAL_THEORY_kjmh-14-2-79.pdf",
        "notebooklm_sources/이제마_B_Track/LEE_KYUNGLOCK_2005_JEMA_MEDICAL_THEORY_kjmh-14-2-79.pdf",
    ),
    (
        "reports/constitution/btrack_pilot/lee2005_pdf_grep_cheonyucho_v1.json",
        "notebooklm_sources/이제마_B_Track/lee2005_pdf_grep_cheonyucho_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/riss_sasang_clinical_pyeonram_2026-06-24.json",
        "notebooklm_sources/이제마_B_Track/riss_sasang_clinical_pyeonram_2026-06-24.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_opac_probe_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_opac_probe_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_p1_library_request_card_v1.txt",
        "notebooklm_sources/이제마_B_Track/cheonyucho_p1_library_request_card_v1.txt",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_external_catalog_probe_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_external_catalog_probe_v1.json",
    ),
    (
        "data/corpus/ijeoma/_inventory/cheonyucho_p344_partial_ingest_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_p344_partial_ingest_v1.json",
    ),
    (
        "data/corpus/ijeoma/originals/cheonyucho_partial/paste.md",
        "notebooklm_sources/이제마_B_Track/cheonyucho_p344_paste_partial.md",
    ),
    (
        "docs/research/raw/SASANG_PYOBYEONG_TOP10_NL_PROXY_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/SASANG_PYOBYEONG_TOP10_NL_PROXY_2026-06-24.md",
    ),
    (
        "reports/constitution/btrack_pilot/sasang_scat_voice_face_bench_v1.json",
        "notebooklm_sources/이제마_B_Track/sasang_scat_voice_face_bench_v1.json",
    ),
    (
        "docs/research/raw/SASANG_SCAT_TOP3_NL_PROXY_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/SASANG_SCAT_TOP3_NL_PROXY_2026-06-24.md",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_grass_vs_chao_verify_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_grass_vs_chao_verify_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/scispace_followup_phase3_manifest_v1.json",
        "notebooklm_sources/이제마_B_Track/scispace_followup_phase3_manifest_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/arc_mkm_control_integrity_grep_v1.json",
        "notebooklm_sources/이제마_B_Track/arc_mkm_control_integrity_grep_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/trading_rl_llm_scispace_dedup_v1.json",
        "data/corpus/ijeoma/_inventory/trading_rl_llm_scispace_dedup_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/arc_architects_ttt_lora_pointer_v1.json",
        "notebooklm_sources/이제마_B_Track/arc_architects_ttt_lora_pointer_v1.json",
    ),
    (
        "docs/research/raw/CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json",
    ),
    (
        "docs/research/raw/CHEONYUCHO_APPENDIX_SWEEP_NL_PROXY_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_APPENDIX_SWEEP_NL_PROXY_2026-06-24.md",
    ),
    (
        "reports/constitution/btrack_pilot/kim_namil_2006_kci_verify_v1.json",
        "notebooklm_sources/이제마_B_Track/kim_namil_2006_kci_verify_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/kim_namil_2006_pdf_grep_cheonyucho_v1.json",
        "notebooklm_sources/이제마_B_Track/kim_namil_2006_pdf_grep_cheonyucho_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/KIM_NAMIL_2006_HANUISAHYEJI_kci_fetch_v1.json",
        "notebooklm_sources/이제마_B_Track/KIM_NAMIL_2006_HANUISAHYEJI_kci_fetch_v1.json",
    ),
    (
        "scripts/grep_cheonyucho_pdf_v1.py",
        "notebooklm_sources/이제마_B_Track/scripts_grep_cheonyucho_pdf_v1.py",
    ),
    (
        "docs/research/raw/KIM_NAMIL_2006_HANUISAHYEJI_medhist.pdf",
        "notebooklm_sources/이제마_B_Track/KIM_NAMIL_2006_HANUISAHYEJI_medhist.pdf",
    ),
    (
        "scripts/fetch_medhist_pdf_v1.py",
        "notebooklm_sources/이제마_B_Track/scripts_fetch_medhist_pdf_v1.py",
    ),
    (
        "scripts/run_cheonyucho_auto_chain_v1.py",
        "notebooklm_sources/이제마_B_Track/scripts_run_cheonyucho_auto_chain_v1.py",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_auto_chain_run_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_auto_chain_run_v1.json",
    ),
    ("scripts/run_cheonyucho_secondary_corpus_dr_v1.py", "notebooklm_sources/이제마_B_Track/scripts_run_cheonyucho_secondary_corpus_dr_v1.py"),
    (
        "docs/research/CHEONYUCHO_SECONDARY_CORPUS_MERGED_LIT_REVIEW_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_SECONDARY_CORPUS_MERGED_LIT_REVIEW_2026-06-24.md",
    ),
    (
        "docs/research/raw/CHEONYUCHO_SECONDARY_CORPUS_v1.json",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_SECONDARY_CORPUS_v1.json",
    ),
    (
        "docs/research/raw/SASANG_CHOBON_DONGMUYUGO_2000_dr.pdf",
        "notebooklm_sources/이제마_B_Track/SASANG_CHOBON_DONGMUYUGO_2000_dr.pdf",
    ),
    (
        "docs/research/raw/DONGMUYUGO_YAKSEONGGA_2001_dr.pdf",
        "notebooklm_sources/이제마_B_Track/DONGMUYUGO_YAKSEONGGA_2001_dr.pdf",
    ),
    (
        "docs/research/raw/LEE_GIBOK_2016_DSSBW_MEDHIST_dr.pdf",
        "notebooklm_sources/이제마_B_Track/LEE_GIBOK_2016_DSSBW_MEDHIST_dr.pdf",
    ),
    (
        "docs/research/raw/CHEONYUCHO_FRAGMENT_LEDGER_v1.json",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_FRAGMENT_LEDGER_v1.json",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_fragment_exa_discover_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_fragment_exa_discover_v1.json",
    ),
    ("scripts/run_cheonyucho_fragment_mine_v1.py", "notebooklm_sources/이제마_B_Track/scripts_run_cheonyucho_fragment_mine_v1.py"),
    (
        "docs/research/raw/GYUKCHIGO_YURYAK_2005_dr.pdf",
        "notebooklm_sources/이제마_B_Track/GYUKCHIGO_YURYAK_2005_dr.pdf",
    ),
    (
        "docs/research/raw/GEUKCHIGO_DOKHAENG_1994_dr.pdf",
        "notebooklm_sources/이제마_B_Track/GEUKCHIGO_DOKHAENG_1994_dr.pdf",
    ),
    (
        "docs/research/raw/DONGMUYUGO_JIPUNGJO_2019_dr.pdf",
        "notebooklm_sources/이제마_B_Track/DONGMUYUGO_JIPUNGJO_2019_dr.pdf",
    ),
    (
        "docs/research/raw/JSCIM_JEMA_OVERVIEW_2020_dr.pdf",
        "notebooklm_sources/이제마_B_Track/JSCIM_JEMA_OVERVIEW_2020_dr.pdf",
    ),
    (
        "docs/research/CHEONYUCHO_ULTRA_DR_MERGED_LIT_REVIEW_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_ULTRA_DR_MERGED_LIT_REVIEW_2026-06-24.md",
    ),
    (
        "docs/research/raw/CHEONYUCHO_ULTRA_TIER0_PROXY_2026-06-24.md",
        "notebooklm_sources/이제마_B_Track/CHEONYUCHO_ULTRA_TIER0_PROXY_2026-06-24.md",
    ),
    (
        "reports/constitution/btrack_pilot/cheonyucho_ultra_dr_belt_run_v1.json",
        "notebooklm_sources/이제마_B_Track/cheonyucho_ultra_dr_belt_run_v1.json",
    ),
    ("scripts/run_cheonyucho_ultra_dr_belt_v1.py", "notebooklm_sources/이제마_B_Track/scripts_run_cheonyucho_ultra_dr_belt_v1.py"),
    (
        "docs/research/raw/SASANG_FORMATION_BIPAK_2020_dr.pdf",
        "notebooklm_sources/이제마_B_Track/SASANG_FORMATION_BIPAK_2020_dr.pdf",
    ),
    (
        "docs/research/raw/JSCIM_JEMA_PHILOSOPHY_2019_dr.pdf",
        "notebooklm_sources/이제마_B_Track/JSCIM_JEMA_PHILOSOPHY_2019_dr.pdf",
    ),
    (
        "docs/research/raw/JSCIM_JEMA_GIJUNGJIN_2024_dr.pdf",
        "notebooklm_sources/이제마_B_Track/JSCIM_JEMA_GIJUNGJIN_2024_dr.pdf",
    ),
    (
        "docs/research/raw/exa_discover_kjmh_3_2_220_pdf.pdf",
        "notebooklm_sources/이제마_B_Track/exa_discover_kjmh_3_2_220_pdf.pdf",
    ),
    (
        "reports/constitution/btrack_pilot/scispace_csv_followup_manifest_v1.json",
        "data/corpus/ijeoma/_inventory/scispace_csv_followup_manifest_v1.json",
    ),
]

# Also mirror into vault/notebooklm_sources tree (restore script path)
VAULT_MIRROR_PREFIX = "vault/notebooklm_sources/data/corpus/ijeoma"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_data_root() -> Path | None:
    env = os.environ.get("MKM_VAULT_ROOT", "").strip()
    if env:
        p = Path(env)
        return p.parent if p.name == "vault" else p
    cand = Path(r"G:\공유 드라이브\MKM_DATA_VAULT")
    return cand if cand.is_dir() else None


def main() -> int:
    data_root = discover_data_root()
    if not data_root:
        log = {
            "schema": "ijeoma_g_vault_manual_sync_v1",
            "synced_at_utc": _utc(),
            "ok": False,
            "reason": "MKM_DATA_VAULT not mounted",
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False))
        return 2

    rows: list[dict] = []
    for src_rel, dst_rel in COPIES:
        src = ROOT / src_rel.replace("/", os.sep)
        dst = data_root / dst_rel.replace("/", os.sep)
        row = {"src": src_rel, "dst": str(dst), "copied": False}
        if not src.is_file():
            row["error"] = "source_missing"
            rows.append(row)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        row["copied"] = True
        row["size"] = dst.stat().st_size
        rows.append(row)
        # vault mirror for corpus paths only
        if src_rel.startswith("data/corpus/ijeoma/"):
            vm = data_root / VAULT_MIRROR_PREFIX / Path(src_rel).relative_to("data/corpus/ijeoma")
            vm.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, vm)
            row["vault_mirror"] = str(vm)

    log = {
        "schema": "ijeoma_g_vault_manual_sync_v1",
        "synced_at_utc": _utc(),
        "data_root": str(data_root),
        "ok": all(r.get("copied") for r in rows if r.get("error") != "source_missing"),
        "copied_count": sum(1 for r in rows if r.get("copied")),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # self-manifest to G
    manifest_dst = data_root / "data/corpus/ijeoma/_inventory/ijeoma_g_vault_manual_sync_2026-06-24.json"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT, manifest_dst)
    vm = data_root / VAULT_MIRROR_PREFIX / "_inventory/ijeoma_g_vault_manual_sync_2026-06-24.json"
    vm.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT, vm)
    print(json.dumps({"ok": log["ok"], "copied": log["copied_count"]}, ensure_ascii=False))
    return 0 if log["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
