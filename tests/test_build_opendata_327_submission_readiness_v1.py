"""build_opendata_327_submission_readiness_v1 — schema smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_opendata_327_submission_readiness_v1.py"


def test_build_readiness_json(tmp_path):
    out = tmp_path / "readiness.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "opendata_327_submission_readiness_v1"
    assert "technical_ready_for_pdf_bundle" in doc
    assert doc["ready_for_kstartup_upload"] is False
