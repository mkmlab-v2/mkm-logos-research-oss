"""
Verify person directory / intake pointer sync and evo_material refs for family+operator.

Exit 0 = pointers, registry scan, and required evo_material files align.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.person_directory_evo_refs_v1 import EVO_MATERIAL_BY_SLUG, EVO_MATERIAL_REQUIRED_SLUGS

REGISTRY_REL = Path("docs/final/artifacts/patient_encounter_registry_v1_latest.json")
PERSON_DIR_REL = Path("docs/final/artifacts/person_directory_v1_latest.json")
POINTER_GLOB = "*_intake_ssot_pointer_v1.json"
MEMORY_SSOT = Path("docs/final/PATIENT_TRACK_B_MEMORY_V1.md")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_person_directory_sync(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    memory_path = root / MEMORY_SSOT
    if not memory_path.is_file():
        errors.append(f"missing memory SSOT: {MEMORY_SSOT.as_posix()}")

    pointers = sorted((root / "reports").glob(POINTER_GLOB))
    pointer_slugs = {p.name.replace("_intake_ssot_pointer_v1.json", "") for p in pointers}

    for rel in (REGISTRY_REL, PERSON_DIR_REL):
        if not (root / rel).is_file():
            errors.append(f"missing registry: {rel.as_posix()}")

    registry = _load_json(root / REGISTRY_REL) if (root / REGISTRY_REL).is_file() else {}
    person = _load_json(root / PERSON_DIR_REL) if (root / PERSON_DIR_REL).is_file() else {}

    scan = registry.get("scan") or {}
    if scan.get("pointers_found") != len(pointers):
        errors.append(
            f"scan.pointers_found={scan.get('pointers_found')} != disk pointers={len(pointers)}"
        )

    reg_encounters = registry.get("encounters") or []
    person_encounters = person.get("encounters") or []
    if len(reg_encounters) != len(person_encounters):
        errors.append("patient_encounter_registry and person_directory encounter counts differ")

    reg_slugs_with_pointer = {
        e.get("slug") for e in reg_encounters if isinstance(e, dict) and e.get("pointer")
    }
    for slug in pointer_slugs:
        if slug not in reg_slugs_with_pointer:
            errors.append(f"pointer on disk but missing registry encounter: {slug}")

    for enc in reg_encounters:
        if not isinstance(enc, dict):
            continue
        slug = enc.get("slug")
        ptr = enc.get("pointer")
        if isinstance(ptr, str):
            if not (root / ptr).is_file():
                errors.append(f"registry pointer missing file: {slug} -> {ptr}")
        if slug in EVO_MATERIAL_REQUIRED_SLUGS:
            evo_rel = EVO_MATERIAL_BY_SLUG[slug]
            if not (root / evo_rel).is_file():
                errors.append(f"missing evo_material for {slug}: {evo_rel}")
            refs = enc.get("evo_material_refs")
            if not refs:
                warnings.append(f"registry row lacks evo_material_refs (rebuild?): {slug}")

    evo_index = registry.get("evo_material_index") or {}
    for slug in EVO_MATERIAL_REQUIRED_SLUGS:
        if slug not in evo_index:
            warnings.append(f"evo_material_index missing slug (rebuild?): {slug}")

    ok = len(errors) == 0
    return {
        "ok": ok,
        "pointers_on_disk": len(pointers),
        "encounter_count": len(reg_encounters),
        "evo_material_slugs": sorted(EVO_MATERIAL_REQUIRED_SLUGS),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check person directory / pointer / evo_material sync.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat warnings as exit 1")
    args = parser.parse_args()
    report = check_person_directory_sync(_ROOT)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["ok"]:
        print(
            f"OK pointers={report['pointers_on_disk']} encounters={report['encounter_count']} "
            f"evo_slugs={len(report['evo_material_slugs'])}"
        )
        for w in report["warnings"]:
            print(f"WARN: {w}")
    else:
        for e in report["errors"]:
            print(f"FAIL: {e}", file=sys.stderr)
    if report["warnings"] and args.strict_warnings:
        return 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
