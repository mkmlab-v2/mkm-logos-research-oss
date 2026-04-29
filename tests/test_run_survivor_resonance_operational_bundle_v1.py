# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 85
# Purpose: Smoke test operational bundle output contract.
# Keywords: pytest, bundle, survivor, resonance
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_survivor_resonance_operational_bundle_v1.py"


def test_operational_bundle_writes_summary(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    proc = subprocess.run(
        ["py", str(SCRIPT), "--output", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "survivor_resonance_operational_bundle_v1"
    assert "policy" in doc and isinstance(doc["policy"], dict)
    assert doc["policy"]["default_exploratory_min_abs_corr"] == 0.08
    assert doc["policy"]["validated_max_go_min_abs_corr"] == 0.082
    assert "runs" in doc and isinstance(doc["runs"], dict)
    assert "snapshots" in doc and isinstance(doc["snapshots"], dict)
    assert "exploratory_gate_output_path" in doc["snapshots"]

