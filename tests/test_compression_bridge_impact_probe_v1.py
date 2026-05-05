# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test compression bridge impact probe artifact generation.
# Keywords: compression, bridge, impact-probe, btrack

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_build_compression_bridge_impact_probe_smoke(tmp_path: Path) -> None:
    out = tmp_path / "probe.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "build_compression_bridge_impact_probe_v1.py"),
            "--recent-trading-days",
            "5",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_bridge_impact_probe_v1"
    assert doc.get("decision") in {"OBSERVED_DIFF", "NO_OBSERVED_DIFF"}
    comp = doc.get("comparison") if isinstance(doc.get("comparison"), dict) else {}
    assert "delta_price_directional_hit_rate" in comp

