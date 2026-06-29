"""Rebuild patient_encounter_registry from intake SSOT pointers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_patient_encounter_registry_v1 import (
    build_encounter_from_pointer,
    build_registry,
    infer_person_kind,
    run,
    slug_from_pointer_filename,
)

ROOT = Path(__file__).resolve().parent.parent


def test_slug_from_pointer_filename() -> None:
    assert slug_from_pointer_filename("choi_hyeonwoo_intake_ssot_pointer_v1.json") == "choi_hyeonwoo"
    assert slug_from_pointer_filename("family_son_kangmin_intake_ssot_pointer_v1.json") == "family_son_kangmin"


def test_infer_person_kind_family_son() -> None:
    ptr = ROOT / "reports/family_son_kangmin_intake_ssot_pointer_v1.json"
    doc = json.loads(ptr.read_text(encoding="utf-8"))
    assert infer_person_kind(doc) == "family_anchor"


def test_build_encounter_kangmin() -> None:
    ptr = ROOT / "reports/family_son_kangmin_intake_ssot_pointer_v1.json"
    enc = build_encounter_from_pointer(ROOT, ptr)
    assert enc["slug"] == "family_son_kangmin"
    assert enc["ref_token"] == "FAMILY-SON-KANGMIN-ANCHOR-V1"
    assert enc["person_kind"] == "family_anchor"
    assert enc["status"] == "family_anchor"
    assert enc["completeness"] == "family_anchor_plus_myeongni"


def test_registry_includes_lifestyle_v2_patients() -> None:
    reg = build_registry(ROOT, None)
    slugs = {e["slug"] for e in reg["encounters"]}
    for expected in (
        "choi_hyeonwoo",
        "jang_jinhee",
        "kim_youngeun",
        "jang_hyeonjin",
        "family_son_kangmin",
        "family_daughter",
        "commander",
    ):
        assert expected in slugs, f"missing {expected}"
    assert "evo_material_index" in reg
    assert "family_son_kangmin" in reg["evo_material_index"]


def test_run_writes_registry_and_person_directory() -> None:
    report = run(ROOT)
    reg_path = ROOT / report["registry_path"]
    person_path = ROOT / report["person_directory_path"]
    assert reg_path.is_file()
    assert person_path.is_file()
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    person = json.loads(person_path.read_text(encoding="utf-8"))
    assert reg["scan"]["pointers_found"] >= 12
    assert reg["scan"]["encounter_count"] >= reg["scan"]["pointers_found"]
    assert person["schema"] == "person_directory_v1"
    assert len(reg["encounters"]) == len(person["encounters"])
