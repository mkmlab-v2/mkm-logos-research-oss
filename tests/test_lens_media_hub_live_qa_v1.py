"""Offline contract checks for lens media hub QA script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_lens_media_hub_live_qa_v1.py"
HTML = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_lens_media_thin_slice_v1.html"
)


def test_lens_media_hub_html_exists() -> None:
    assert HTML.is_file(), f"missing hub HTML: {HTML}"


def test_lens_media_hub_offline_qa_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--offline"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
