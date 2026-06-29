"""Universal root research→implementation bridge smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_universal_root_research_impl_bridge_v1() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_universal_root_research_impl_bridge_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (
            ROOT / "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert doc["schema"] == "universal_root_research_impl_bridge_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["bridge_ok"] is True
