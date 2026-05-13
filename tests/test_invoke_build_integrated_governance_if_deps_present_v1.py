"""invoke_build_integrated_governance_if_deps_present_v1: skip when deps missing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_INVOKER = _REPO / "scripts" / "invoke_build_integrated_governance_if_deps_present_v1.py"
_BUILDER = _REPO / "scripts" / "build_integrated_governance_v1.py"
_FIX_BIB = _REPO / "scripts" / "fixtures" / "kospi_biblical_single_lane_commercial_gate_v1_ci_minimal_hold_v1.json"
_FIX_MYE = _REPO / "scripts" / "fixtures" / "kospi_myeongri_standalone_commercial_gate_v1_ci_minimal_hold_v1.json"
_FIX_SAS = _REPO / "scripts" / "fixtures" / "kospi_sasang_single_lane_commercial_gate_v1_ci_minimal_hold_v1.json"
_CFG = _REPO / "docs" / "final" / "artifacts" / "integrated_governance_config_v1.json"


def test_invoker_script_exists() -> None:
    assert _INVOKER.is_file()


def test_integrated_governance_config_committed() -> None:
    p = _REPO / "docs" / "final" / "artifacts" / "integrated_governance_config_v1.json"
    assert p.is_file()
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj.get("schema") == "integrated_governance_config_v1"
    assert isinstance(obj.get("weights"), dict)


def test_build_integrated_governance_cli_accepts_ci_minimal_gate_fixtures(tmp_path: Path) -> None:
    """Structural contract: same fixtures CI copies before the deps-gated invoker."""
    pytest.importorskip("jsonschema")
    out = tmp_path / "integrated_governance_v1_latest.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_BUILDER),
            "--config-json",
            str(_CFG),
            "--biblical-json",
            str(_FIX_BIB),
            "--myeongri-json",
            str(_FIX_MYE),
            "--sasang-json",
            str(_FIX_SAS),
            "--out-json",
            str(out),
            "--validate-digest-schema",
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert out.is_file()
    obj = json.loads(out.read_text(encoding="utf-8"))
    assert obj.get("schema") == "integrated_governance_v1"
    assert obj.get("final_regime") == "HOLD"
    assert obj.get("final_action_allowed") is False


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
