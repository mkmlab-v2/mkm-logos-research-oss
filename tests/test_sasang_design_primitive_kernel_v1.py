from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/sasang_design_primitive_kernel_v1.schema.json"
CHARTER = ROOT / "docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md"
CHECK = ROOT / "scripts/check_sasang_design_primitive_kernel_v1.py"


def test_charter_and_kernel_paths_exist():
    assert CHARTER.is_file()
    assert KERNEL.is_file()
    assert SCHEMA.is_file()


def test_kernel_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    instance = json.loads(KERNEL.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_product_depth_personadiary_excludes_extensions():
    doc = json.loads(KERNEL.read_text(encoding="utf-8"))
    pd = doc["product_depth"]["personadiary.com"]
    assert "pathology" in pd["primitives"]
    assert pd["extensions"] == []


def test_harmony_v1_stub_flags_clinical_ban_deferred():
    harmony = json.loads(KERNEL.read_text(encoding="utf-8"))["primitives"]["harmony"]
    assert harmony.get("v1_stub") is True
    assert harmony.get("clinical_constitution_ban_ui_v1_1") is True


def test_check_script_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
