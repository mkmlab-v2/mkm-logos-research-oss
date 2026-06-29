#!/usr/bin/env python3
"""Shared helpers for domain prophecy registry/config (B-track)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
MERGE_MANIFEST = ROOT / "data/commander/domain_prophecy_merge_manifest_v1.json"
GP_SCHEMA = ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_registry(path: Path | None = None) -> dict[str, Any]:
    p = path or REGISTRY
    return load_json(p)


def find_domain(registry: dict[str, Any], domain_id: str) -> dict[str, Any] | None:
    for row in registry.get("domains") or []:
        if isinstance(row, dict) and row.get("domain_id") == domain_id:
            return row
    return None


def load_domain_config(domain_row: dict[str, Any]) -> dict[str, Any]:
    rel = domain_row.get("config_path")
    if not rel:
        raise FileNotFoundError(f"domain {domain_row.get('domain_id')} missing config_path")
    path = ROOT / str(rel).replace("/", "\\")
    return load_json(path)


def load_merge_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or MERGE_MANIFEST
    return load_json(p)


def pack_path_for_domain(domain_id: str, manifest: dict[str, Any] | None = None) -> Path | None:
    doc = manifest or load_merge_manifest()
    rel = (doc.get("packs") or {}).get(domain_id)
    if not rel:
        return None
    return ROOT / str(rel).replace("/", "\\")


def validate_general_prophecy_registry(doc: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = load_json(GP_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")
