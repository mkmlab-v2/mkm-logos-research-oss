"""RQ-026 matrix variant sweep."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts/run_sasang_temperament_agents_matrix_sweep_v1.py"
V1_1 = ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"
MARKET = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"


def test_matrix_v1_1_spec_exists() -> None:
    doc = json.loads(V1_1.read_text(encoding="utf-8"))
    assert doc.get("version") == "1.1.0"
    assert doc.get("parent_matrix") == "pathology_transition_matrix_v1.json"


def test_matrix_sweep_runs(tmp_path: Path) -> None:
    if not MARKET.is_file():
        pytest.skip("market psych v2 missing")
    out = tmp_path / "sweep.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SWEEP),
            "--out",
            str(out),
            "--fractions",
            "0.1,0.2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_temperament_agents_matrix_sweep_v1"
    assert len(doc.get("rows") or []) == 4  # 2 variants × 2 fractions
    rec = doc.get("recommended_candidate") or {}
    assert rec.get("variant") in ("v1_1", "v1_2")
