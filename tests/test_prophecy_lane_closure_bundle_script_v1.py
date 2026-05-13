# @MKM12-METADATA
# Type: Logic
# Purpose: regression — prophecy lane closure bundle script exists and matches SSOT steps.
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1"


def test_closure_bundle_script_declares_pipeline() -> None:
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "verify_p0_constitution_gate_paths.ps1" in text
    assert "check_btrack_prophecy_chain_prereqs_v1.py" in text
    assert "run_prophecy_alignment_pytest.ps1" in text
    assert "Invoke-SafeOpsSurfaceCheck.ps1" in text
    assert "build_trading_go_nogo_status_v1.py" in text
    assert "prophecy_lane_closure_bundle_v1_latest.json" in text
