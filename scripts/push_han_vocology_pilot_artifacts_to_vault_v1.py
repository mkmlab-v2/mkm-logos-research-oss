#!/usr/bin/env python3
"""Mirror Han Vocology KM-VHI pilot artifacts to MKM_DATA_VAULT (B-track · M16)."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/han_vocology_vault_mirror_v1_latest.json"

ARTIFACTS: list[str] = [
    "reports/han_vocology_km_vhi_pilot_records.jsonl",
    "reports/han_vocology_km_vhi_pilot_summary_v1_latest.json",
    "reports/han_vocology_km_vhi_pilot_cohort_gate_v1_latest.json",
    "reports/han_vocology_pilot_closure_v1_latest.json",
    "reports/han_vocology_km_vhi_pilot_jsonl_validation_v1_latest.json",
    "docs/final/artifacts/han_vocology_multisite_registry_v1_latest.json",
    "docs/final/artifacts/han_vocology_completion_status_v1_latest.json",
    "docs/final/artifacts/km_vhi_questionnaire_v0_1_latest.json",
    "docs/final/artifacts/han_vocology_notebooklm_sources_checklist_v1_latest.json",
    "reports/han_vocology_pilot_final_report_v1_latest.json",
    "reports/han_vocology_pilot_final_report_v1_latest.md",
    "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json",
    "reports/han_vocology_osce_rubric_validation_v1_latest.json",
    "reports/han_vocology_graduation_gate_v1_latest.json",
    "reports/han_vocology_graduation_gate_v1_latest.md",
    "reports/han_vocology_graduation_gate_validation_v1_latest.json",
    "docs/final/artifacts/han_vocology_cb_dashboard_pilot_crosscheck_v1_latest.json",
    "docs/research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vault_dest() -> Path | None:
    env = os.environ.get("MKM_VAULT_ROOT")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env) / "notebooklm_sources" / "한의음성학" / "pilot_artifacts")
        candidates.append(Path(env) / "vault" / "notebooklm_sources" / "한의음성학" / "pilot_artifacts")
    candidates.append(
        Path(r"G:\공유 드라이브\MKM_DATA_VAULT\notebooklm_sources\한의음성학\pilot_artifacts")
    )
    candidates.append(
        Path(r"G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\한의음성학\pilot_artifacts")
    )
    for dest in candidates:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            return dest
        except OSError:
            continue
    return None


def main() -> int:
    dest = _vault_dest()
    if dest is None:
        log: dict[str, Any] = {
            "schema": "han_vocology_vault_mirror_v1",
            "ok": False,
            "skipped": True,
            "reason": "vault_not_mounted",
            "generated_at_utc": _utc(),
        }
        OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "skipped": True, "reason": "vault_not_mounted"}, ensure_ascii=False))
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    for rel in ARTIFACTS:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = dest / Path(rel).name
        shutil.copy2(src, dst)
        copied.append(rel)

    stamp = dest / "_COPIED_AT_UTC.txt"
    stamp.write_text(_utc() + "\n", encoding="utf-8")

    log = {
        "schema": "han_vocology_vault_mirror_v1",
        "ok": not missing,
        "generated_at_utc": _utc(),
        "dest": str(dest),
        "copied_count": len(copied),
        "copied": copied,
        "missing": missing,
    }
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": log["ok"], "copied": len(copied), "dest": str(dest), "missing": missing},
            ensure_ascii=False,
        )
    )
    return 0 if log["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
