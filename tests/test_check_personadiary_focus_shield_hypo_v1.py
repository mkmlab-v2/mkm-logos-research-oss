"""PersonaDiary focus shield hypo gate tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_personadiary_focus_shield_hypo_v1.py"
A4_GATE = ROOT / "scripts/check_notebooklm_clinician_no_ops_merge_v1.py"
BUILD = ROOT / "scripts/build_notebooklm_clinician_sync_pack_v1.py"


def test_focus_shield_gate_exit_zero() -> None:
    cp = subprocess.run([sys.executable, str(GATE)], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_clinician_no_ops_merge_gate_exit_zero() -> None:
    cp = subprocess.run([sys.executable, str(A4_GATE)], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_build_clinician_pack_then_a4_strict() -> None:
    if not BUILD.is_file():
        return
    bcp = subprocess.run([sys.executable, str(BUILD)], cwd=str(ROOT), capture_output=True, text=True)
    assert bcp.returncode == 0, bcp.stderr + bcp.stdout
    cp = subprocess.run(
        [sys.executable, str(A4_GATE), "--require-built-pack"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
