from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_dss_confidence_calibration_log_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    refresh = root / "scripts" / "ops" / "run_dss_slot_mapping_refresh.py"
    out = root / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_confidence_calibration_latest.json"
    r = subprocess.run(
        [sys.executable, str(refresh)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_dss_confidence_calibration_v1"
    assert doc.get("confidence_mode") == "v2"
    assert isinstance(doc.get("confidence_params"), dict)
    full = doc.get("full", {})
    canon = doc.get("canonical_only", {})
    assert float(full.get("mean_confidence_boost", 0.0)) >= 0.8
    assert float(canon.get("mean_confidence_boost", 0.0)) >= 0.8
