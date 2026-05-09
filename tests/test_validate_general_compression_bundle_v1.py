"""Contract tests: validate_general_compression_bundle hard-lock (NO_GO_HIGH_COMPRESSION_LOCK)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_GO = ROOT / "tests/fixtures/general_compression_bundle_minimal_v1/manifest_go.json"
MANIFEST_NO_GO = ROOT / "tests/fixtures/general_compression_bundle_minimal_v1/manifest_no_go.json"


def _run_validate(manifest: Path) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "validate_general_compression_bundle.py"),
        "--manifest",
        str(manifest),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return int(cp.returncode)


def test_validate_bundle_passes_when_stress_go() -> None:
    assert MANIFEST_GO.is_file()
    rc = _run_validate(MANIFEST_GO)
    assert rc == 0


def test_validate_bundle_fails_when_stress_no_go_high_compression_lock() -> None:
    assert MANIFEST_NO_GO.is_file()
    rc = _run_validate(MANIFEST_NO_GO)
    assert rc == 1
