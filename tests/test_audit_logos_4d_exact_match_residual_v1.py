# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_exact_match_residual_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_logos_4d_exact_match_residual_v1.py"), "--sample", "5"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads((ROOT / "reports/logos_4d_exact_match_residual_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_4d_exact_match_residual_v1"
    assert doc["summary"]["compared"] == 31102
    assert doc["summary"]["mismatch_count"] > 0
