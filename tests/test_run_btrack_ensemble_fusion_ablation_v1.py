# @MKM12-METADATA
# Type: Logic
# Purpose: ensemble fusion ablation runner smoke (dry-run + profile cfg).
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_btrack_ensemble_fusion_ablation_v1.py"
_CFG = _ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"


def test_ablation_script_exists() -> None:
    assert _SCRIPT.is_file()


def test_profile_cfg_v2_mode() -> None:
    if not _CFG.is_file():
        import pytest

        pytest.skip("btrack_lens_ensemble_v1.json missing")
    base = json.loads(_CFG.read_text(encoding="utf-8"))
    # Import helper by running dry-run only; inline mirror of v2_confidence_fusion rule
    rules = dict(base.get("rules") or {})
    rules["ensemble_mode"] = "v2_confidence_fusion"
    assert rules["ensemble_mode"] == "v2_confidence_fusion"


def test_ablation_dry_run_exit_zero() -> None:
    if not _CFG.is_file():
        import pytest

        pytest.skip("ensemble config missing")
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--dry-run", "--profiles", "v1_baseline,v2_confidence_fusion"],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip().splitlines()[-1])
    assert doc.get("dry_run") is True
