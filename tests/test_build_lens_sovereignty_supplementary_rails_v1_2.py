#!/usr/bin/env python3
"""Smoke tests for lens sovereignty supplementary rails v1.2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_supplementary_rails_v1_2_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/build_lens_sovereignty_supplementary_rails_v1_2.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = ROOT / "docs/final/artifacts/lens_sovereignty_supplementary_rails_v1_2_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_sovereignty_supplementary_rails_v1_2"
    assert "rails" in doc
    assert "pack0b_lora" in doc["rails"]
    assert doc["rails"]["pack0b_lora"].get("forbidden_in_market_verdict") is True
    assert doc["supplementary_verdict"] in (
        "SUPP_ALIGNED",
        "SUPP_PARTIAL",
        "SUPP_FAIL",
        "SUPP_PENDING",
    )
