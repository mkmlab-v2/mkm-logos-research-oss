"""Smoke: alert_aramaic_insight_cap_threshold_drift_v1 writes drift alert JSON (cleans default artifact if present)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "alert_aramaic_insight_cap_threshold_drift_v1.py"
ART = ROOT / "docs" / "final" / "artifacts" / "aramaic_insight_cap_bucket_threshold_drift_alert_latest.json"


def test_alert_insight_cap_threshold_drift_cli_smoke() -> None:
    before = ART.exists()
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert ART.is_file()
        doc = json.loads(ART.read_text(encoding="utf-8"))
        assert doc.get("schema") == "aramaic_insight_cap_threshold_drift_alert_v1"
    finally:
        if ART.exists() and not before:
            ART.unlink()
