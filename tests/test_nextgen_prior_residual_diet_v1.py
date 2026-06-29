"""[HYPO] Prior residual diet Step 1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_prior_residual_diet_v1_latest.json"
)
SCRIPT = ROOT / "scripts/run_nextgen_prior_residual_diet_v1.py"


def test_prior_residual_diet_exit0_byte_exact():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "nextgen_prior_residual_diet_v1"
    rec = doc.get("recommended_diet") or {}
    z = rec.get("sidecar_zero_bill")
    assert z is not None
    assert z["byte_exact_subset_parity"] == 1.0
