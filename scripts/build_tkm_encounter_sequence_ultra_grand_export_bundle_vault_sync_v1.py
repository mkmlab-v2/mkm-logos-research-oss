#!/usr/bin/env python3
"""Build TKM encounter_sequence ultra-grand export bundle vault sync manifest [HYPO]."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
MANIFEST_OUT = ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_manifest_v1_latest.json"
MANIFEST_ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_export_manifest_v1_latest.json"

P63_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p63_gate_v1_latest.json"
ULTRA_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
GRAND_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"

ULTRA_GRAND_EXPORT_REL_PATHS = (
    "reports/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json",
    "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json",
    "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json",
    "reports/tkm_encounter_sequence_full_post_export_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_full_post_export_closure_v1_latest.json",
    "reports/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json",
    "reports/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json",
    "reports/encounter_sequence_weekly_report_v1_latest.json",
    "reports/tkm_encounter_sequence_ops_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_p57_gate_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_manifest_v1_latest.json",
    "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_grand_export_manifest_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_p58_gate_v1_latest.json",
    "reports/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json",
    "reports/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json",
    "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json",
    "reports/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json",
    "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json",
    "docs/final/artifacts/tkm_encounter_sequence_p63_gate_v1_latest.json",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_entry(rel: str) -> dict[str, Any]:
    path = ROOT / rel.replace("/", os.sep)
    if not path.is_file():
        return {"rel_path": rel.replace("\\", "/"), "exists": False}
    return {
        "rel_path": rel.replace("\\", "/"),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _vault_root() -> Path | None:
    raw = (os.environ.get("MKM_VAULT_ROOT") or "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_dir() else None
    default = Path(r"G:\공유 드라이브\MKM_DATA_VAULT\vault")
    return default if default.is_dir() else None


def _mirror_to_vault(entries: list[dict[str, Any]]) -> dict[str, Any]:
    vault = _vault_root()
    if vault is None:
        return {
            "vault_mirror_attempted": False,
            "vault_mirror_ok": True,
            "vault_mirror_skipped": True,
            "reason": "vault_unavailable",
        }
    target = vault / "btrack_artifacts_verified" / "tkm_encounter_sequence" / "ultra_grand"
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    for entry in entries:
        if not entry.get("exists"):
            missing.append(str(entry.get("rel_path")))
            continue
        src = ROOT / str(entry["rel_path"]).replace("/", os.sep)
        dst_name = Path(str(entry["rel_path"])).name
        shutil.copy2(src, target / dst_name)
        copied.append(dst_name)
    if MANIFEST_OUT.is_file():
        shutil.copy2(MANIFEST_OUT, target / MANIFEST_OUT.name)
        copied.append(MANIFEST_OUT.name)
    return {
        "vault_mirror_attempted": True,
        "vault_mirror_ok": len(missing) == 0,
        "vault_mirror_skipped": False,
        "vault_target": str(target).replace("\\", "/"),
        "copied_count": len(copied),
        "copied_files": copied,
        "missing_count": len(missing),
        "missing_files": missing,
    }


def build(*, mirror_vault: bool = True) -> dict[str, Any]:
    p63 = _load(P63_GATE)
    ultra = _load(ULTRA_CLOSURE)
    grand_vault = _load(GRAND_VAULT_SYNC)
    weekly = _load(WEEKLY)

    entries = [_file_entry(rel) for rel in ULTRA_GRAND_EXPORT_REL_PATHS]
    all_exist = all(e.get("exists") for e in entries)
    manifest = {
        "schema": "tkm_encounter_sequence_ultra_grand_export_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "research_only": True,
        "cloud_upload_forbidden": True,
        "files": entries,
        "file_count": len(entries),
        "files_present_count": sum(1 for e in entries if e.get("exists")),
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MANIFEST_OUT, MANIFEST_ARTIFACT)

    vault_result = _mirror_to_vault(entries) if mirror_vault else {
        "vault_mirror_attempted": False,
        "vault_mirror_ok": True,
        "vault_mirror_skipped": True,
        "reason": "mirror_disabled",
    }

    ultra_grand_export_bundle_vault_sync_ok = (
        p63.get("gate_ok") is True
        and ultra.get("ultra_grand_post_export_closure_ok") is True
        and grand_vault.get("grand_export_bundle_vault_sync_ok") is True
        and all_exist
        and manifest.get("files_present_count") == manifest.get("file_count")
        and vault_result.get("vault_mirror_ok") is True
        and weekly.get("weekly_ok") is True
        and grand_vault.get("cloud_upload_forbidden") is True
    )

    return {
        "schema": "tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "ultra_grand_export_bundle_vault_sync_ok": ultra_grand_export_bundle_vault_sync_ok,
        "p63_gate_ok": p63.get("gate_ok"),
        "ultra_grand_post_export_closure_ok": ultra.get("ultra_grand_post_export_closure_ok"),
        "grand_export_bundle_vault_sync_ok": grand_vault.get("grand_export_bundle_vault_sync_ok"),
        "weekly_ok": weekly.get("weekly_ok"),
        "manifest_file_count": manifest.get("file_count"),
        "manifest_files_present_count": manifest.get("files_present_count"),
        "gates_ok_count": ultra.get("gates_ok_count"),
        "cloud_upload_forbidden": True,
        "cloud_upload_attempted": False,
        "vault_mirror": vault_result,
        "manifest_path": str(MANIFEST_OUT).replace("\\", "/"),
        "manifest_artifact_path": str(MANIFEST_ARTIFACT).replace("\\", "/"),
        "base_grand_manifest_ref": "docs/final/artifacts/tkm_encounter_sequence_grand_export_manifest_v1_latest.json",
        "note_ko": "P64 ultra-grand export bundle vault sync [HYPO][NON_GATING]; P63 closure + vault ultra_grand/ mirror; cloud MCP upload 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-vault-mirror", action="store_true")
    ap.add_argument("--mirror-artifact", action="store_true", default=True)
    ap.add_argument("--no-mirror-artifact", action="store_false", dest="mirror_artifact")
    args = ap.parse_args()
    doc = build(mirror_vault=not args.no_vault_mirror)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mirror_artifact:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, ARTIFACT)
    print(
        json.dumps(
            {
                "ok": doc.get("ultra_grand_export_bundle_vault_sync_ok"),
                "files": doc.get("manifest_files_present_count"),
                "vault_skipped": (doc.get("vault_mirror") or {}).get("vault_mirror_skipped"),
            }
        )
    )
    return 0 if doc.get("ultra_grand_export_bundle_vault_sync_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
