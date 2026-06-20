#!/usr/bin/env python3
"""Vault 2 reference pointer registry — validate only ([HYPO] / research_only).

  py scripts/check_mkm_reference_pointer_registry_v1.py
  py scripts/check_mkm_reference_pointer_registry_v1.py --registry storage/meta/...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SCRIPT_ROOT / "storage/meta/mkm_reference_pointer_registry_v1.json"
REQUIRED_FORBIDDEN_MERGE = frozenset({"ops_memory_index"})


def load_registry(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_reference_pointer_registry_v1":
        raise ValueError(f"unexpected registry schema: {doc.get('schema')!r}")
    return doc


def validate_registry(root: Path, doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pointers = doc.get("pointers") or []
    max_pointers = int(doc.get("max_pointers") or 64)
    needles = tuple(doc.get("forbidden_governance_needles") or ())
    seen_ids: set[str] = set()

    if len(pointers) > max_pointers:
        errors.append(f"pointer count {len(pointers)} exceeds max_pointers {max_pointers}")

    for idx, ptr in enumerate(pointers):
        label = f"pointers[{idx}]"
        if ptr.get("schema") != "mkm_reference_pointer_v1":
            errors.append(f"{label}: schema must be mkm_reference_pointer_v1")
        ptr_id = ptr.get("id")
        if not ptr_id:
            errors.append(f"{label}: missing id")
        elif ptr_id in seen_ids:
            errors.append(f"{label}: duplicate id {ptr_id!r}")
        else:
            seen_ids.add(str(ptr_id))

        if ptr.get("inject_policy") != "on_demand_only":
            errors.append(f"{label}: inject_policy must be on_demand_only")

        forbidden = set(ptr.get("forbidden_merge_into") or [])
        if not REQUIRED_FORBIDDEN_MERGE.issubset(forbidden):
            missing = sorted(REQUIRED_FORBIDDEN_MERGE - forbidden)
            errors.append(f"{label}: forbidden_merge_into missing {missing}")

        resource = ptr.get("resource_path")
        if not resource:
            errors.append(f"{label}: missing resource_path")
        else:
            res_path = root / str(resource)
            if not res_path.is_file():
                errors.append(f"{label}: resource_path missing on disk: {resource}")

        repo_path = ptr.get("repo_path")
        if repo_path and not (root / str(repo_path)).is_file():
            errors.append(f"{label}: repo_path missing on disk: {repo_path}")

        haystack = " ".join(
            str(ptr.get(k, ""))
            for k in ("id", "essence", "resource_path", "repo_path")
        ) + " " + " ".join(str(t) for t in (ptr.get("domain_tags") or []))
        for needle in needles:
            if needle.lower() in haystack.lower():
                errors.append(f"{label}: forbidden governance needle {needle!r} in pointer metadata")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    registry_path = args.registry if args.registry.is_absolute() else root / args.registry
    if not registry_path.is_file():
        print(f"FAIL: registry missing: {registry_path}", file=sys.stderr)
        return 1

    try:
        doc = load_registry(registry_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    errors = validate_registry(root, doc)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    count = len(doc.get("pointers") or [])
    print(f"reference pointer registry gate: OK ({count} pointers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
