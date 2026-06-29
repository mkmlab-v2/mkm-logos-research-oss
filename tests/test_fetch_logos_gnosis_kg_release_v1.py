"""Smoke: Gnosis release fetch report (skip-download when tar present)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fetch_logos_gnosis_kg_release_v1.py"
DEST = ROOT / "storage/external_kg/gnosis_v0.9.3"
REPORT = ROOT / "reports/logos_gnosis_kg_fetch_v1_latest.json"


def test_fetch_skip_download_when_tar_present():
    if not (DEST / "gnosis-v0.9.3.tar.gz").is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-download"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_gnosis_kg_fetch_v1"
    assert doc["ok"] is True
    assert doc["files"]["hebrew-words.json"]["exists"] is True
    assert doc["files"]["greek-words.json"]["exists"] is True
