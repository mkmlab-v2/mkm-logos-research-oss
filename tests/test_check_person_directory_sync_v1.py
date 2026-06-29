"""Person directory sync gate."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_patient_encounter_registry_v1 import run as rebuild_registry
from scripts.check_person_directory_sync_v1 import check_person_directory_sync

ROOT = Path(__file__).resolve().parent.parent


def test_check_sync_after_rebuild() -> None:
    rebuild_registry(ROOT)
    report = check_person_directory_sync(ROOT)
    assert report["ok"], report["errors"]


def test_evo_material_refs_on_family_and_commander() -> None:
    rebuild_registry(ROOT)
    reg = json.loads(
        (ROOT / "docs/final/artifacts/person_directory_v1_latest.json").read_text(encoding="utf-8")
    )
    by_slug = {e["slug"]: e for e in reg["encounters"]}
    for slug in ("family_son_kangmin", "family_daughter", "commander"):
        enc = by_slug[slug]
        assert enc.get("evo_material_refs"), slug
        assert enc["evo_material_refs"][0]["exists"] == "true"
    assert set(reg.get("evo_material_index", {}).keys()) >= {
        "family_son_kangmin",
        "family_daughter",
        "commander",
    }


def test_jiyoon_has_person_kind_deprecated() -> None:
    rebuild_registry(ROOT)
    reg = json.loads(
        (ROOT / "docs/final/artifacts/patient_encounter_registry_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    jiyoon = next(e for e in reg["encounters"] if e["slug"] == "jiyoon")
    assert jiyoon.get("person_kind") == "deprecated"
