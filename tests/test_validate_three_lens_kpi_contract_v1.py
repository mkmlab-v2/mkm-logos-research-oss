from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_three_lens_kpi_contract_v1.py"
CONTRACT = ROOT / "docs" / "final" / "artifacts" / "THREE_LENS_KPI_CONTRACT_V1.json"


def test_validate_three_lens_kpi_contract_v1_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--contract-json", str(CONTRACT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert '"ok": true' in cp.stdout.lower()
