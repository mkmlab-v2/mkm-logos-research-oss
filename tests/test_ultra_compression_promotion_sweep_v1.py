"""Promotion sweep must not write Track A active report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SWEEP = ROOT / "scripts/run_ultra_compression_promotion_sweep_v1.py"
APPLY = ROOT / "scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py"


def test_sweep_dry_run_lists_variants() -> None:
    cp = subprocess.run(
        [sys.executable, str(SWEEP), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload.get("dry_run") is True
    assert len(payload.get("variants") or []) >= 4


def test_apply_without_human_flag_exits_nonzero() -> None:
    cp = subprocess.run(
        [sys.executable, str(APPLY), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 2


def test_active_report_path_not_default_sweep_out(tmp_path: Path) -> None:
    """Sweep default out is promotion candidate, not active."""
    from scripts.run_ultra_compression_promotion_sweep_v1 import OUT_CANDIDATE

    assert OUT_CANDIDATE.resolve() != ACTIVE.resolve()


def test_default_runner_loads_promotion_signoff_when_present() -> None:
    from scripts.run_ultra_compression_default import PROMOTION_SIGNOFF, _promotion_signoff_run_config

    if not PROMOTION_SIGNOFF.is_file():
        return
    cfg = _promotion_signoff_run_config()
    assert cfg is not None
    assert cfg.get("domain_relaxed_max_saving_overrides")
