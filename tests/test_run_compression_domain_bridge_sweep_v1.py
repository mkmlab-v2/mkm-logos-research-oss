# Keywords: compression domain bridge sweep

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bridge_sweep_writes_artifact() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_compression_domain_bridge_sweep_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "docs/final/artifacts/compression_domain_bridge_sweep_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_domain_bridge_sweep_v1"
    assert len(doc.get("variants") or []) >= 4
