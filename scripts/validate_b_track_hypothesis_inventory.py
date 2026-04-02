# @MKM12-METADATA
# Type: Logic
# Purpose: Validate B_TRACK_HYPOTHESIS_INVENTORY_V1.json against draft-07 schema.
"""CLI: py scripts/validate_b_track_hypothesis_inventory.py [--path PATH] [--no-check-links]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_INV = _ROOT / "docs" / "final" / "artifacts" / "B_TRACK_HYPOTHESIS_INVENTORY_V1.json"
_DEFAULT_SCHEMA = _ROOT / "docs" / "final" / "B_TRACK_HYPOTHESIS_INVENTORY_SCHEMA.json"

# Logical names per CONSTITUTION §4.5.1 — paths relative to repo root.
_ARTIFACT_ENTRY_ID_SOURCES: dict[str, str] = {
    "CROSS_REF_DSS_TO_STATES_DRAFT": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json",
    "SASANG_CROSS_REF_DRAFT": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json",
    "LOGOS_STATE_MAPPING_V1": "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json",
}


def load_entry_id_set(target_artifact: str, root: Path) -> set[str]:
    """Return valid reference ids for an SSOT artifact.

    - CROSS_REF / SASANG: ``entries[].entry_id``
    - LOGOS_STATE_MAPPING_V1: ``str(assignments[].state_id)`` (1–16), for future cross_links that cite state keys.
    """
    rel = _ARTIFACT_ENTRY_ID_SOURCES.get(target_artifact)
    if rel is None:
        raise KeyError(target_artifact)
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if target_artifact == "LOGOS_STATE_MAPPING_V1":
        return {str(a["state_id"]) for a in data.get("assignments", []) if "state_id" in a}
    ids: set[str] = set()
    for ent in data.get("entries", []):
        eid = ent.get("entry_id")
        if eid is not None:
            ids.add(str(eid))
    return ids


def collect_cross_link_errors(
    doc: dict,
    root: Path,
    *,
    id_cache: dict[str, set[str]] | None = None,
) -> list[str]:
    """Return human-readable errors for dangling ``cross_links`` references; empty if OK."""
    cache = id_cache if id_cache is not None else {}
    errors: list[str] = []
    for ent in doc.get("entries", []):
        hid = ent.get("hypothesis_id", "?")
        links = ent.get("cross_links")
        if not links:
            continue
        if not isinstance(links, list):
            errors.append(f"{hid}: cross_links must be a list")
            continue
        for i, block in enumerate(links):
            if not isinstance(block, dict):
                errors.append(f"{hid}: cross_links[{i}] must be an object")
                continue
            tgt = block.get("target_artifact")
            ids = block.get("entry_ids")
            if tgt is None:
                errors.append(f"{hid}: cross_links[{i}] missing target_artifact")
                continue
            if tgt not in _ARTIFACT_ENTRY_ID_SOURCES:
                errors.append(
                    f"{hid}: cross_links[{i}] unknown target_artifact {tgt!r} "
                    f"(known: {sorted(_ARTIFACT_ENTRY_ID_SOURCES)})",
                )
                continue
            if ids is None:
                errors.append(f"{hid}: cross_links[{i}] missing entry_ids")
                continue
            if not isinstance(ids, list):
                errors.append(f"{hid}: cross_links[{i}] entry_ids must be a list")
                continue
            try:
                if tgt not in cache:
                    cache[tgt] = load_entry_id_set(tgt, root)
                valid = cache[tgt]
            except FileNotFoundError as e:
                errors.append(f"{hid}: SSOT missing for {tgt}: {e}")
                continue
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                errors.append(f"{hid}: failed reading {tgt}: {e}")
                continue
            for raw in ids:
                eid = str(raw)
                if eid not in valid:
                    errors.append(
                        f"{hid}: cross_links[{i}] entry_id {eid!r} not in {tgt}",
                    )
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description="Validate B-track hypothesis inventory JSON.")
    p.add_argument("--path", type=Path, default=_DEFAULT_INV, help="Inventory JSON path")
    p.add_argument("--schema", type=Path, default=_DEFAULT_SCHEMA, help="JSON Schema path")
    p.add_argument(
        "--no-check-links",
        action="store_true",
        help="Skip cross_links SSOT resolution (schema only).",
    )
    args = p.parse_args()
    try:
        import jsonschema
    except ImportError:
        print("jsonschema required: pip install jsonschema", file=sys.stderr)
        return 2
    if not args.path.is_file():
        print(f"missing: {args.path}", file=sys.stderr)
        return 1
    if not args.schema.is_file():
        print(f"missing: {args.schema}", file=sys.stderr)
        return 1
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    doc = json.loads(args.path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    if not args.no_check_links:
        errs = collect_cross_link_errors(doc, _ROOT)
        if errs:
            print("cross_links SSOT errors:", file=sys.stderr)
            for line in errs:
                print(f"  {line}", file=sys.stderr)
            return 1
    print(f"OK: {args.path.relative_to(_ROOT)} ({len(doc.get('entries', []))} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
