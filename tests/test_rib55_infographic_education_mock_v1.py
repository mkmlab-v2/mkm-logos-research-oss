"""rib55 elementary education HTML mock builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_rib55_infographic_education_mock_v1.py"
OUT = ROOT / "reports/demo/rib55_infographic_education_mock_v1.html"


def test_build_rib55_infographic_education_mock_exit0():
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert OUT.is_file()
    html = OUT.read_text(encoding="utf-8")
    assert "교육용" in html
    assert "55°" not in html
    assert "send_gate HOLD" in html or "research_only" in html
    report = json.loads((ROOT / "reports/rib55_infographic_education_mock_v1_latest.json").read_text(encoding="utf-8"))
    assert report["ok"] is True
