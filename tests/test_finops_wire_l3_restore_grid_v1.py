"""FinOps L3 restore grid (holdout bench only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/finops_wire_l3_restore_grid_v1_latest.json"


def test_finops_l3_restore_grid_runs():
    cp = subprocess.run(
        [sys.executable, "scripts/run_finops_wire_l3_restore_grid_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr[-800:]
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("research_only") is True
    cells = doc.get("cells") or []
    assert len(cells) >= 3
    trading = [c for c in cells if c.get("scenario") == "trading"]
    assert trading
    assert all(c.get("atom_wire_roundtrip_rate") == 1.0 for c in trading)
