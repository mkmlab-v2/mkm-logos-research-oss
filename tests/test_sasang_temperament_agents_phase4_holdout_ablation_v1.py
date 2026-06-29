"""RQ-026 phase-4 holdout + matrix ablation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "scripts/build_sasang_temperament_agents_phase4_holdout_ablation_v1.py"
MARKET = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"


def test_phase4_holdout_ablation_runs(tmp_path: Path) -> None:
    if not MARKET.is_file():
        pytest.skip("market psych v2 missing")
    out = tmp_path / "phase4.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(PHASE4),
            "--out",
            str(out),
            "--holdout-fraction",
            "0.2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_temperament_agents_phase4_holdout_ablation_v1"
    assert doc.get("research_only") is True
    assert doc.get("n_days_holdout", 0) >= 1
    assert "matrix_coupled" in doc
    assert "no_matrix_legacy" in doc
    assert "ablation_delta_holdout" in doc
    delta = doc.get("ablation_delta_holdout") or {}
    assert "temperament_consistency_matrix_minus_none" in delta
