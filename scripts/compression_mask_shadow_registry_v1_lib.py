"""[HYPO-3] Artifact-only MASK shadow registry — manifest hashes + staging pointers (B-track).

research_only · no domain_router mutation · pointer swap only for future v2 stub wiring.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REGISTRY_ENTRIES: list[dict[str, str]] = [
    {
        "entry_id": "biz_template_manifest",
        "vertical_id": "zone_h_en_business_v1",
        "wire_family": "BIZ_MASK",
        "repo_rel_path": "codebook/templates/zone_h_en_business_templates_manifest_v1.json",
        "staging_env_key": "MKM_BIZ_MASK_CATALOG_MANIFEST",
    },
    {
        "entry_id": "biz_template_catalog",
        "vertical_id": "zone_h_en_business_v1",
        "wire_family": "BIZ_MASK",
        "repo_rel_path": "codebook/templates/zone_h_en_business_templates_v1.jsonl",
        "staging_env_key": "MKM_BIZ_MASK_CATALOG_JSONL",
    },
    {
        "entry_id": "biz_shadow_bind_spec",
        "vertical_id": "zone_h_en_business_v1",
        "wire_family": "BIZ_MASK",
        "repo_rel_path": "docs/final/artifacts/compression_en_business_shadow_router_bind_v1.json",
        "staging_env_key": "MKM_BIZ_MASK_SHADOW_BIND_SPEC",
    },
    {
        "entry_id": "cs_template_manifest",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "repo_rel_path": "codebook/templates/zone_ko_premium_cs_templates_manifest_v1.json",
        "staging_env_key": "MKM_CS_MASK_CATALOG_MANIFEST",
    },
    {
        "entry_id": "cs_template_catalog",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "repo_rel_path": "codebook/templates/zone_ko_premium_cs_templates_v1.jsonl",
        "staging_env_key": "MKM_CS_MASK_CATALOG_JSONL",
    },
    {
        "entry_id": "cs_wtt_overlay_manifest",
        "vertical_id": "zone_ko_premium_cs_v1",
        "wire_family": "CS_MASK",
        "repo_rel_path": "data/compression/fixtures/zone_ko_premium_cs_wtt_overlay_scan_manifest_v1.json",
        "staging_env_key": "MKM_CS_WTT_OVERLAY_MANIFEST",
    },
    {
        "entry_id": "spiking_closeout",
        "vertical_id": "compression_sku_ab",
        "wire_family": "META",
        "repo_rel_path": "reports/compression_spiking_closeout_v1.json",
        "staging_env_key": "MKM_COMPRESSION_SPIKING_CLOSEOUT",
    },
]

HYPO_RUNNERS: list[dict[str, str]] = [
    {
        "hypo_id": "HYPO-1a",
        "script": "scripts/run_en_business_template_overlay_scan_v1.py",
    },
    {
        "hypo_id": "HYPO-2",
        "script": "scripts/run_en_business_shadow_router_bind_v1.py",
    },
    {
        "hypo_id": "HYPO-1b",
        "script": "scripts/run_ko_premium_cs_wtt_template_overlay_scan_v1.py",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head_sha(workspace_root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip() or None
    except Exception:
        return None


def resolve_entry(path: Path, meta: dict[str, str]) -> dict[str, Any]:
    exists = path.is_file()
    row: dict[str, Any] = {
        "entry_id": meta["entry_id"],
        "vertical_id": meta["vertical_id"],
        "wire_family": meta["wire_family"],
        "repo_rel_path": meta["repo_rel_path"],
        "staging_env_key": meta["staging_env_key"],
        "exists": exists,
        "sha256": sha256_file(path) if exists else None,
    }
    if exists and path.suffix == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(doc, dict):
                if "catalog_sha256" in doc:
                    row["catalog_sha256"] = doc["catalog_sha256"]
                if "row_count" in doc:
                    row["row_count"] = doc["row_count"]
                if "shadow_shard_id" in doc:
                    row["shadow_shard_id"] = doc["shadow_shard_id"]
        except Exception:
            pass
    return row


def build_registry(*, workspace_root: Path = ROOT) -> dict[str, Any]:
    entries = [
        resolve_entry(workspace_root / meta["repo_rel_path"], meta)
        for meta in REGISTRY_ENTRIES
    ]
    missing = [e["entry_id"] for e in entries if not e["exists"]]
    staging_env: dict[str, str] = {}
    for e in entries:
        if e["exists"]:
            staging_env[str(e["staging_env_key"])] = str(e["repo_rel_path"])

    return {
        "schema": "compression_mask_shadow_registry_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "shadow_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "production_router_unchanged": True,
        "workspace_root": workspace_root.as_posix(),
        "git_head_sha": git_head_sha(workspace_root),
        "baseline_sha_note": "ab873947e8 BIZ 13-row lock; registry pins manifest hashes for pointer swap",
        "fail_comp_note": "Staging pointers only — no v2 stub ACTIVE wiring; no secrets in registry.",
        "entries": entries,
        "hypo_runners": HYPO_RUNNERS,
        "staging_env_pointers": staging_env,
        "aggregate": {
            "entry_count": len(entries),
            "missing_entry_ids": missing,
            "all_entries_present": len(missing) == 0,
        },
        "reproduce": "py scripts/run_compression_mask_shadow_registry_sync_v1.py",
    }


def mirror_registry_files(
    registry: dict[str, Any],
    *,
    mirror_root: Path,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    copied: list[str] = []
    skipped: list[str] = []
    mirror_root.mkdir(parents=True, exist_ok=True)
    for entry in registry.get("entries") or []:
        if not entry.get("exists"):
            skipped.append(str(entry.get("entry_id")))
            continue
        rel = str(entry.get("repo_rel_path") or "")
        src = workspace_root / rel
        dst = mirror_root / rel.replace("/", "__")
        shutil.copy2(src, dst)
        copied.append(rel)
    manifest_path = mirror_root / "_mirror_manifest.json"
    mirror_doc = {
        "schema": "compression_mask_shadow_registry_mirror_v1",
        "generated_at_utc": _utc(),
        "mirror_root": mirror_root.as_posix(),
        "copied_count": len(copied),
        "copied_repo_paths": copied,
        "skipped_entry_ids": skipped,
        "registry_git_head_sha": registry.get("git_head_sha"),
    }
    manifest_path.write_text(json.dumps(mirror_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return mirror_doc


def write_registry_artifacts(
    registry: dict[str, Any],
    *,
    report_path: Path,
    staging_path: Path,
) -> None:
    payload = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(payload, encoding="utf-8")
