"""Product completion DoD builder smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_product_completion_dod_builder_runs():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_inquiry_product_completion_dod_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr[-500:]
    out = ROOT / "reports/logos_inquiry_product_completion_dod_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_inquiry_product_completion_dod_v1"
    assert doc.get("send_gate") == "HOLD"
    assert "layers" in doc
