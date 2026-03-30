from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_weight_sweep_generates_report() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "sweep_gematria_bridge_weights.py"
    out = root / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_BRIDGE_WEIGHT_SWEEP_V1.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "multilens_gematria_4d_bridge_weight_sweep_v1"
    assert int(doc.get("grid_size", 0)) > 0
    assert isinstance(doc.get("top5"), list)
