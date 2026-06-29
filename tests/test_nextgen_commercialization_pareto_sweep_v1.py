"""[HYPO] Commercialization Pareto sweep spec + runner smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_COMMERCIALIZATION_PARETO_SWEEP_SPEC_V1.json"
)
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_commercialization_pareto_sweep_v1_latest.json"
)
SCRIPT = ROOT / "scripts/run_nextgen_commercialization_pareto_sweep_v1.py"


def test_spec_has_sla_and_grid():
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    assert doc["schema"] == "nextgen_commercialization_pareto_sweep_spec_v1"
    assert doc["step_0_sla_contract"]["byte_exact_gate"]
    assert doc["sweep_grid_smoke"]["keep_ratio"]


def test_smoke_sweep_exit0_and_spine_parity():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--smoke"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "nextgen_commercialization_pareto_sweep_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    for row in doc["sweep_rows"]:
        assert row["byte_exact_subset_parity"] == 1.0
