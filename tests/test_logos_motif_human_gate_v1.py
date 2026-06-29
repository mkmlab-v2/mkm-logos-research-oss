"""Human gate queue validate + merge smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "docs/final/artifacts/logos_motif_human_gate_validation_v1_latest.json"
EXTENSIONS = ROOT / "docs/final/artifacts/logos_motif_human_gate_extensions_v1.json"


def _run(script: str, *args: str) -> None:
    proc = subprocess.run(
        [sys.executable, f"scripts/{script}", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_human_gate_queue_validates() -> None:
    _run("validate_logos_motif_human_gate_queue_v1.py")
    report = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert report["pass"] is True
    assert report["ok_count"] == 60


def test_human_gate_merge_all_extensions() -> None:
    _run("apply_logos_motif_human_gate_merge_v1.py", "--hd-auto-all", "--skip-validate")
    ext = json.loads(EXTENSIONS.read_text(encoding="utf-8"))
    assert ext["entry_count"] == 60
    reg_proc = subprocess.run(
        [sys.executable, "scripts/build_logos_motif_registry_top100_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert reg_proc.returncode == 0
    reg = json.loads(
        (ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert reg["enabled_count"] == 100
    assert reg["placeholder_count"] == 0
