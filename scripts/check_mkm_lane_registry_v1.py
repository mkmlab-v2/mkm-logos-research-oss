#!/usr/bin/env python3
"""Validate MKM_LANE_REGISTRY_V1.json against schema and path pointers (no network)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]


def _root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


REGISTRY_REL = "docs/final/artifacts/MKM_LANE_REGISTRY_V1.json"
SCHEMA_REL = "docs/final/schemas/mkm_lane_registry_v1.schema.json"


def _glob_has_match(root: Path, pattern: str) -> bool:
    """True if at least one path exists under pattern (best-effort for ** globs)."""
    p = pattern.replace("\\", "/")
    if "**" not in p:
        return (root / p).exists()
    base = p.split("**", 1)[0].rstrip("/")
    if not base:
        return True
    base_path = root / base
    return base_path.exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    ap.add_argument("--skip-path-exists", action="store_true", help="Schema only; skip read/mdc checks")
    args = ap.parse_args()
    root = _root(args.workspace_root)
    registry_path = root / REGISTRY_REL
    schema_path = root / SCHEMA_REL

    if not registry_path.is_file():
        print(f"FAIL missing registry: {REGISTRY_REL}", file=sys.stderr)
        return 1
    if not schema_path.is_file():
        print(f"FAIL missing schema: {SCHEMA_REL}", file=sys.stderr)
        return 1

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    if jsonschema is None:
        print("WARN jsonschema not installed; schema validation skipped", file=sys.stderr)
    else:
        jsonschema.validate(instance=registry, schema=schema)

    errors: list[str] = []
    lane_ids = [lane["lane_id"] for lane in registry.get("lanes", [])]
    if len(lane_ids) != len(set(lane_ids)):
        errors.append("duplicate lane_id in registry")

    if not args.skip_path_exists:
        for lane in registry.get("lanes", []):
            lid = lane.get("lane_id", "?")
            for rel in lane.get("read_dependencies", []):
                if rel.endswith(".mdc"):
                    if not (root / rel).is_file():
                        errors.append(f"{lid}: missing mdc read_dependency {rel}")
                elif rel.endswith(".md"):
                    if not (root / rel).is_file():
                        errors.append(f"{lid}: missing read_dependency {rel}")
            mdc = lane.get("mdc_pointer")
            if mdc and not (root / mdc).is_file():
                errors.append(f"{lid}: missing mdc_pointer {mdc}")
            for g in lane.get("write_globs", []):
                if not _glob_has_match(root, g):
                    errors.append(f"{lid}: write_glob has no match yet: {g}")

    if errors:
        print("MKM lane registry check: FAIL", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"MKM lane registry check: OK ({len(registry.get('lanes', []))} lanes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
