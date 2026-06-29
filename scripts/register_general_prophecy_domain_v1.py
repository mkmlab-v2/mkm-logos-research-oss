#!/usr/bin/env python3
"""Register a general_prophecy domain pack into merge manifest + refresh registry [B-track].

Validates pack against GENERAL_PROPHECY_SCHEMA_V1, optionally merges into
docs/final/artifacts/general_prophecy_latest.json, updates domain registry status.

research_only · send_gate HOLD · no Track A wiring
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
MANIFEST = ROOT / "data/commander/domain_prophecy_merge_manifest_v1.json"
DEFAULT_PRIMARY = ROOT / "tests/fixtures/general_prophecy_registry_sample_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/general_prophecy_latest.json"

sys.path.insert(0, str(ROOT))
from scripts.domain_prophecy_lib_v1 import (  # noqa: E402
    find_domain,
    load_json,
    load_merge_manifest,
    pack_path_for_domain,
    rel,
    validate_general_prophecy_registry,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_manifest_entry(domain_id: str, pack_path: Path, manifest: dict[str, Any]) -> bool:
    packs = manifest.setdefault("packs", {})
    key = str(pack_path).replace("\\", "/")
    if packs.get(domain_id) == key:
        return False
    packs[domain_id] = rel(pack_path)
    manifest["generated_at_utc"] = _utc()
    return True


def _activate_registry(domain_id: str, registry: dict[str, Any], config_path: str | None) -> bool:
    row = find_domain(registry, domain_id)
    if not row:
        raise SystemExit(f"domain_id not in registry: {domain_id}")
    changed = False
    if row.get("status") != "active":
        row["status"] = "active"
        changed = True
    if config_path and row.get("config_path") != config_path:
        row["config_path"] = config_path
        changed = True
    if changed:
        registry["generated_at_utc"] = _utc()
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain-id", required=True)
    ap.add_argument("--pack", type=Path, default=None, help="Pack JSON; default from merge manifest")
    ap.add_argument("--domain-tag", default=None, help="Ensure tag present on all questions")
    ap.add_argument("--config-path", default=None, help="Registry config_path to set on activate")
    ap.add_argument("--activate-registry", action="store_true")
    ap.add_argument("--refresh-artifact", action="store_true", help="Run generate_general_prophecy merge")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", type=Path, default=None)
    args = ap.parse_args()

    manifest = load_merge_manifest(MANIFEST)
    pack = args.pack or pack_path_for_domain(args.domain_id, manifest)
    if not pack or not pack.is_file():
        print(f"FAIL: pack not found for {args.domain_id}", file=sys.stderr)
        return 2

    pack_doc = load_json(pack)
    if args.domain_tag:
        tag = args.domain_tag.strip()
        for q in pack_doc.get("questions") or []:
            if not isinstance(q, dict):
                continue
            tags = q.setdefault("domain_tags", [])
            if tag not in tags:
                tags.append(tag)

    validate_general_prophecy_registry(pack_doc)
    n_questions = len(pack_doc.get("questions") or [])

    manifest_changed = _ensure_manifest_entry(args.domain_id, pack, manifest)
    registry_changed = False
    registry = load_json(REGISTRY)
    if args.activate_registry:
        cfg = args.config_path or f"data/commander/domain_configs/{args.domain_id}_config_v1.json"
        registry_changed = _activate_registry(args.domain_id, registry, cfg)

    refresh_exit = None
    if args.refresh_artifact and not args.dry_run:
        proc = subprocess.run(
            [
                PY,
                "scripts/generate_general_prophecy_v1.py",
                "-i",
                str(DEFAULT_PRIMARY),
                "--merge-from",
                str(pack),
                "-o",
                str(DEFAULT_OUT),
                "--stub-forecasts",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        refresh_exit = proc.returncode
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    report = {
        "schema": "domain_prophecy_register_report_v1",
        "generated_at_utc": _utc(),
        "domain_id": args.domain_id,
        "pack_path": rel(pack),
        "n_questions": n_questions,
        "domain_tag": args.domain_tag,
        "manifest_changed": manifest_changed,
        "registry_changed": registry_changed,
        "refresh_artifact_exit": refresh_exit,
        "dry_run": args.dry_run,
        "research_only": True,
        "send_gate": "HOLD",
        "ok": refresh_exit in (None, 0),
        "reproduce": (
            f"py scripts/register_general_prophecy_domain_v1.py --domain-id {args.domain_id} "
            "--activate-registry --refresh-artifact"
        ),
    }

    if not args.dry_run:
        if manifest_changed:
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if registry_changed:
            REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.report:
            out = args.report
        else:
            out = ROOT / f"reports/domain_prophecy_register_{args.domain_id}_latest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "domain_id": args.domain_id, "n_questions": n_questions}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
