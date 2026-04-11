"""apply_general_prophecy_registry_patches_v1: subprocess + fixture registry."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_general_prophecy_registry_patches_v1.py"
REG_FIX = ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
PATCH_FIX = ROOT / "tests" / "fixtures" / "general_prophecy_registry_patch_sample_v1.json"
PATCH_TRACK = ROOT / "tests" / "fixtures" / "general_prophecy_registry_patch_track_v1.json"


def test_apply_patch_updates_layer3(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    shutil.copy(REG_FIX, reg)
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry",
            str(reg),
            "--patch",
            str(PATCH_FIX),
            "--output",
            str(reg),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr + out.stdout
    doc = json.loads(reg.read_text(encoding="utf-8"))
    q0 = doc["questions"][0]
    assert q0["layer3_interpretation_ref"] == "docs/final/NOTEBOOKLM_AUTOMATED_PATCH_TEST_V1.md"


def test_apply_patch_sets_prophecy_track_and_personalization_scope(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    shutil.copy(REG_FIX, reg)
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry",
            str(reg),
            "--patch",
            str(PATCH_TRACK),
            "--output",
            str(reg),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr + out.stdout
    doc = json.loads(reg.read_text(encoding="utf-8"))
    q0 = doc["questions"][0]
    assert q0["question_id"] == "demo.binary.sample_01"
    assert q0["prophecy_track"] == "financial"
    assert q0["personalization_scope_v1"]["mode"] == "none"
    assert q0["personalization_scope_v1"]["consent_scope"] == ["l1_forecast"]


def test_unknown_question_id_exits_2(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    shutil.copy(REG_FIX, reg)
    bad_patch = tmp_path / "bad.json"
    bad_patch.write_text(
        json.dumps(
            {
                "schema": "general_prophecy_registry_patch_v1",
                "patches": [{"question_id": "no.such.id", "layer3_interpretation_ref": "x"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--registry", str(reg), "--patch", str(bad_patch)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 2
