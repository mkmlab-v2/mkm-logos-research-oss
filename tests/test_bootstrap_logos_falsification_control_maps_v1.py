# Keywords: bootstrap_logos_falsification_control_maps_v1

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/bootstrap_logos_falsification_control_maps_v1.py"


def test_bootstrap_control_maps_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    counter = ROOT / "docs/final/artifacts/logos_symbolic_event_map_counterfactual_v1.json"
    assert counter.is_file()
    doc = json.loads(counter.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_symbolic_event_map_v1"
    joseph = next(s for s in doc["symbols"] if s["symbol_id"] == "joseph_famine_storage")
    assert joseph["direction_bias"] == "up"
