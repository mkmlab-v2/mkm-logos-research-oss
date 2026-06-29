"""
Rebuild patient / person directory from reports/*_intake_ssot_pointer_v1.json.

Machine SSOT: docs/final/artifacts/patient_encounter_registry_v1_latest.json
Human index: docs/final/PATIENT_TRACK_B_MEMORY_V1.md (sections maintained separately)

Also writes person_directory_v1_latest.json (same encounters; schema alias for unified naming).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.person_directory_evo_refs_v1 import (  # noqa: E402
    build_evo_material_index,
    evo_material_refs_for_slug,
)

REGISTRY_REL = Path("docs/final/artifacts/patient_encounter_registry_v1_latest.json")
PERSON_DIR_REL = Path("docs/final/artifacts/person_directory_v1_latest.json")
POINTER_GLOB = "*_intake_ssot_pointer_v1.json"

EXCLUDED_FROM_PATIENT_COUNT = [
    "patient_intake_fusion_bundle_soeum_in_latest.json",
    "patient_intake_fusion_bundle_soyang_in_latest.json",
    "patient_intake_fusion_bundle_taeeum_in_latest.json",
    "patient_intake_fusion_bundle_taeyang_in_latest.json",
    "commander_2026_myeongni_full_v1_latest.json",
]

MEMORY_SSOT = "docs/final/PATIENT_TRACK_B_MEMORY_V1.md"


def _workspace_root() -> Path:
    return _ROOT


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug_from_pointer_filename(name: str) -> str:
    suffix = "_intake_ssot_pointer_v1.json"
    if not name.endswith(suffix):
        raise ValueError(f"unexpected pointer filename: {name}")
    return name[: -len(suffix)]


def infer_person_kind(doc: dict[str, Any]) -> str:
    explicit = doc.get("person_kind")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    status = str(doc.get("status") or "")
    rail = str(doc.get("rail") or "")
    if status == "deprecated":
        return "deprecated"
    if status == "operator_profile" or rail == "operator_profile":
        return "operator_profile"
    if status == "family_anchor" or rail == "family":
        return "family_anchor"
    return "clinical_patient"


def infer_status(doc: dict[str, Any], person_kind: str) -> str:
    status = doc.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    if person_kind == "operator_profile":
        return "operator_profile"
    if person_kind == "family_anchor":
        return "family_anchor"
    if person_kind == "deprecated":
        return "deprecated"
    return "active"


def infer_completeness(doc: dict[str, Any]) -> str:
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return "pointer_only"
    if paths.get("lifestyle_management_fixture"):
        return "intake_myeongni_lifestyle_physician_gold"
    if paths.get("integrated_guide_md") or paths.get("family_anchor"):
        return "family_anchor_plus_myeongni"
    if paths.get("intake") and paths.get("bundle_json"):
        if paths.get("physician_assist_turn_json") or paths.get("wellness_report"):
            return "full_chain_plus_wellness_physician_turn"
        return "full_chain_intake_myeongni_bundle"
    if paths.get("solution_report") or paths.get("commander_profile"):
        return "solution_anchor_plus_myeongni"
    return "pointer_only"


def infer_rail(doc: dict[str, Any], person_kind: str) -> str:
    rail = doc.get("rail")
    if isinstance(rail, str) and rail.strip():
        return rail.strip()
    if person_kind == "operator_profile":
        return "operator"
    if person_kind == "family_anchor":
        return "family"
    return "Track B"


def normalize_family_links(links: Any, slug: str) -> list[dict[str, Any]]:
    if not isinstance(links, list):
        return []
    out: list[dict[str, Any]] = []
    for item in links:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if "slug" not in row and isinstance(row.get("pointer"), str):
            ptr = row["pointer"]
            if ptr.endswith("_intake_ssot_pointer_v1.json"):
                try:
                    row["slug"] = slug_from_pointer_filename(Path(ptr).name)
                except ValueError:
                    pass
        out.append(row)
    return out


def build_encounter_from_pointer(root: Path, pointer_path: Path) -> dict[str, Any]:
    doc = _load_json(pointer_path)
    slug = slug_from_pointer_filename(pointer_path.name)
    person_kind = infer_person_kind(doc)
    rel_pointer = pointer_path.relative_to(root).as_posix()
    evo_refs = evo_material_refs_for_slug(root, slug, doc)
    encounter: dict[str, Any] = {
        "ref_token": doc.get("ref_token") or f"{slug.upper()}-UNKNOWN",
        "slug": slug,
        "display_label": doc.get("display_label") or slug,
        "person_kind": person_kind,
        "status": infer_status(doc, person_kind),
        "completeness": infer_completeness(doc),
        "pointer": rel_pointer,
        "rail": infer_rail(doc, person_kind),
    }
    links = normalize_family_links(doc.get("family_links"), slug)
    if links:
        encounter["family_links"] = links
    tags = doc.get("cohort_tags")
    if isinstance(tags, list) and tags:
        encounter["cohort_tags"] = tags
    note = doc.get("note")
    if isinstance(note, str) and note.strip():
        encounter["note"] = note.strip()
    legacy_of = doc.get("legacy_of")
    if isinstance(legacy_of, str) and legacy_of.strip():
        encounter["legacy_of"] = legacy_of.strip()
    if evo_refs:
        encounter["evo_material_refs"] = evo_refs
    return encounter


def merge_legacy_encounters(
    scanned: dict[str, dict[str, Any]], existing: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Keep deprecated rows without pointer files (e.g. jiyoon)."""
    if not existing:
        return list(scanned.values())
    for enc in existing.get("encounters") or []:
        if not isinstance(enc, dict):
            continue
        slug = enc.get("slug")
        if not isinstance(slug, str) or slug in scanned:
            continue
        if enc.get("status") == "deprecated" or enc.get("person_kind") == "deprecated":
            enc = dict(enc)
            enc.setdefault("person_kind", "deprecated")
            enc.setdefault("status", "deprecated")
            scanned[slug] = enc
    return sorted(scanned.values(), key=lambda e: (e.get("person_kind", ""), e.get("slug", "")))


def build_registry(root: Path, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    reports = root / "reports"
    pointers = sorted(reports.glob(POINTER_GLOB))
    scanned: dict[str, dict[str, Any]] = {}
    intakes_found = 0
    for ptr in pointers:
        enc = build_encounter_from_pointer(root, ptr)
        scanned[enc["slug"]] = enc
        doc = _load_json(ptr)
        paths = doc.get("paths") or {}
        if isinstance(paths, dict) and paths.get("intake"):
            intakes_found += 1

    encounters = merge_legacy_encounters(scanned, existing)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema": "patient_encounter_registry_v1",
        "version": "1.1.0",
        "directory_alias": "person_directory_v1",
        "generated_at_utc": now,
        "rail_default": "Track B",
        "adjudication_model": "physician_final_authority_non_auto",
        "memory_ssot": MEMORY_SSOT,
        "evo_material_index": build_evo_material_index(root),
        "evo_sync_check_cli": "py scripts/check_person_directory_sync_v1.py",
        "encounters": encounters,
        "excluded_from_patient_count": list(EXCLUDED_FROM_PATIENT_COUNT),
        "regenerate_cli": "py scripts/build_patient_encounter_registry_v1.py",
        "render_wellness_all_cli": "py scripts/render_patient_wellness_report_v1.py --all-active --update-pointer",
        "build_physician_assist_all_cli": (
            "py scripts/build_han_physician_clinical_assist_turn_v1.py --all-active --update-pointer"
        ),
        "scan": {
            "pointers_found": len(pointers),
            "intakes_found": intakes_found,
            "encounter_count": len(encounters),
        },
    }


def write_registry(root: Path, registry: dict[str, Any]) -> tuple[Path, Path]:
    reg_path = root / REGISTRY_REL
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    person = dict(registry)
    person["schema"] = "person_directory_v1"
    person_path = root / PERSON_DIR_REL
    person_path.write_text(json.dumps(person, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return reg_path, person_path


def run(root: Path | None = None) -> dict[str, Any]:
    root = root or _workspace_root()
    existing_path = root / REGISTRY_REL
    existing = _load_json(existing_path) if existing_path.is_file() else None
    registry = build_registry(root, existing)
    reg_path, person_path = write_registry(root, registry)
    return {
        "registry_path": str(reg_path.relative_to(root)),
        "person_directory_path": str(person_path.relative_to(root)),
        "encounter_count": registry["scan"]["encounter_count"],
        "pointers_found": registry["scan"]["pointers_found"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild patient/person directory from intake pointers.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON to stdout")
    args = parser.parse_args()
    report = run()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"OK encounters={report['encounter_count']} pointers={report['pointers_found']} "
            f"-> {report['registry_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
