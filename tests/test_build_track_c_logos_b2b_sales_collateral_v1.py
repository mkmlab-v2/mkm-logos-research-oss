"""Smoke tests for Track C Logos B2B sales collateral builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_track_c_logos_b2b_sales_collateral_v1.py"
SLIDE = ROOT / "docs/final/artifacts/track_c_logos_b2b_exec_summary_slide_v1_latest.md"
DEMO = ROOT / "docs/final/artifacts/track_c_logos_redacted_demo_excerpt_v1_latest.md"


def test_sales_collateral_builder_runs() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1)
    assert SLIDE.is_file()
    assert DEMO.is_file()
    slide = SLIDE.read_text(encoding="utf-8")
    demo = DEMO.read_text(encoding="utf-8")
    assert "DRAFT_AUTO" in slide
    assert "NON_GATING" in slide or "[NON_GATING]" in slide
    assert "C:\\workspace" not in demo
    assert "docs/final/artifacts/" not in demo
    assert "sample-001" not in demo


def test_redact_paths_helper() -> None:
    from scripts.build_track_c_logos_b2b_sales_collateral_v1 import _redact_paths

    raw = "source: C:\\workspace\\docs\\final\\artifacts\\foo.json"
    out = _redact_paths(raw)
    assert "C:\\workspace" not in out
    assert "[REDACTED" in out
