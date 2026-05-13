"""invoke_build_integrated_governance_if_deps_present_v1: skip when deps missing."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_INVOKER = _REPO / "scripts" / "invoke_build_integrated_governance_if_deps_present_v1.py"


def test_invoker_script_exists() -> None:
    assert _INVOKER.is_file()


def test_invoker_skips_when_workspace_has_no_gate_artifacts(tmp_path: Path) -> None:
    """Empty temp dir has no KOSPI gates → exit 0 (skip), no exception."""
    r = subprocess.run(
        [sys.executable, str(_INVOKER), "--workspace-root", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0
    assert "SKIP" in (r.stderr or "")
