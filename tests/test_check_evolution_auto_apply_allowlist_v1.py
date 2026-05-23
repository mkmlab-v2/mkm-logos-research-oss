"""Evolution auto-apply allowlist contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_allowlist_artifact_loads() -> None:
    path = ROOT / "docs/final/artifacts/evolution_auto_apply_allowlist_v1_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema"] == "evolution_auto_apply_allowlist_v1"
    assert doc["rails"]["btrack_price"]["auto_apply_mode"] == "parameter_only"
    assert "neutral_bps" in doc["rails"]["btrack_price"]["allowed_parameter_targets"]
    assert doc["rails"]["commander_hypothesis"]["auto_apply_mode"] == "none"


def test_check_allowlist_script_exit_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_evolution_auto_apply_allowlist_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_btrack_neutral_bps_allowed() -> None:
    from evolution_auto_apply_allowlist_v1 import assert_btrack_parameter_target_allowed

    assert_btrack_parameter_target_allowed("neutral_bps")


def test_btrack_forbidden_target_raises() -> None:
    from evolution_auto_apply_allowlist_v1 import assert_btrack_parameter_target_allowed

    try:
        assert_btrack_parameter_target_allowed("live_order_routing")
    except ValueError:
        return
    raise AssertionError("expected ValueError for forbidden target")
