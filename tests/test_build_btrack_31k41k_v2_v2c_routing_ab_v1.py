"""Smoke test for v2 vs v2c routing A/B builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_btrack_31k41k_v2_v2c_routing_ab_v1.py"
OUT = ROOT / "reports" / "btrack_31k41k_v2_v2c_routing_ab_v1_latest.json"


def test_routing_ab_builds() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_31k41k_v2_v2c_routing_ab_v1"
    assert doc["research_only"] is True
    assert "v2" in doc and "v2c" in doc
    assert doc["v2"]["routing_policy"] == "v2"
    assert doc["v2c"]["routing_policy"] == "v2c"
