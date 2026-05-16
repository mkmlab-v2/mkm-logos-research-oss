# Keywords: compression board ms correlation report

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_correlation_report() -> None:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_compression_board_ms_correlation_report_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "docs/final/artifacts/compression_board_ms_correlation_report_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_board_ms_correlation_report_v1"
    assert doc.get("compression_kpi", {}).get("ultra_saving_policy_ok") is True
    assert doc["derived"]["correlation_claim_allowed"] is False
